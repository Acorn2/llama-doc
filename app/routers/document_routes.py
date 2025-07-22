"""
文档相关的API路由
"""
import os
import uuid
import time
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db, Document
from app.schemas import (
    DocumentUploadResponse, TaskStatus, DocumentInfo, 
    DocumentStatusResponse, DuplicateCheckResponse
)
from app.utils.file_utils import calculate_content_md5, is_duplicate_file
from app.utils.file_storage import file_storage_manager
from app.core.document_processor import DocumentProcessor
from app.core.vector_store import VectorStoreManager
from app.core.agent_core import DocumentAnalysisAgent

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={404: {"description": "Not found"}},
)

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传PDF文档 - 支持重复检测和腾讯云COS存储"""
    
    # 先读取文件内容，验证文件类型和大小
    file_content = await file.read()
    
    # 验证文件类型
    from app.core.document_processor import DocumentProcessor
    from app.schemas import FileType
    from pathlib import Path
    
    doc_processor = DocumentProcessor()
    
    if not doc_processor.is_supported_file(file.filename):
        supported_types = list(doc_processor.SUPPORTED_TYPES.keys())
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型。支持的类型: {', '.join(supported_types)}"
        )
    
    # 获取文件扩展名并确定文件类型
    file_ext = Path(file.filename).suffix.lower()
    file_type = FileType.from_extension(file_ext)
    
    # 验证文件大小（50MB限制）
    if len(file_content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过50MB")
    
    try:
        # 计算MD5等不涉及数据库的操作
        file_md5 = calculate_content_md5(file_content)
        logger.info(f"文件 {file.filename} MD5: {file_md5}, 类型: {file_type}")
        
        # 检查是否存在重复文件
        existing_doc_id = is_duplicate_file(db, file_md5)
        if existing_doc_id:
            # 获取已存在的文档信息
            existing_doc = db.query(Document).filter(Document.id == existing_doc_id).first()
            
            logger.info(f"发现重复文件，返回已存在的文档ID: {existing_doc_id}")
            
            return DocumentUploadResponse(
                document_id=existing_doc_id,
                filename=existing_doc.filename,
                status=TaskStatus(existing_doc.status),
                upload_time=existing_doc.upload_time,
                file_type=FileType(existing_doc.file_type) if existing_doc.file_type else None,
                message=f"文件已存在，状态: {existing_doc.status}（重复检测基于MD5）"
            )
        
        # 生成唯一文档ID
        document_id = str(uuid.uuid4())
        
        # 开始一个新的事务
        try:
            # 使用文件存储管理器保存文件
            storage_result = file_storage_manager.save_file(
                file_content=file_content,
                document_id=document_id,
                filename=file.filename
            )
            
            if not storage_result["success"]:
                raise HTTPException(status_code=500, detail=f"文件保存失败: {storage_result['error']}")
            
            # 创建数据库记录
            db_document = Document(
                id=document_id,
                filename=file.filename,
                file_path=storage_result["file_path"],
                file_size=storage_result["file_size"],
                file_md5=file_md5,
                status="pending",
                file_type=file_type.value,  # 设置文件类型
                # COS相关字段
                cos_object_key=storage_result["cos_object_key"],
                cos_file_url=storage_result["cos_file_url"],
                cos_etag=storage_result["cos_etag"],
                storage_type=storage_result["storage_type"]
            )
            db.add(db_document)
            db.commit()
            
            storage_info = "腾讯云COS" if storage_result["storage_type"] == "cos" else "本地存储"
            logger.info(f"新文档上传成功({storage_info})，类型: {file_type.value}，等待处理: {document_id}")
            
            return DocumentUploadResponse(
                document_id=document_id,
                filename=file.filename,
                status=TaskStatus.PENDING,
                upload_time=datetime.now(),
                file_type=file_type,
                message=f"文档上传成功({storage_info})，正在等待处理..."
            )
        except Exception as db_error:
            # 回滚事务
            db.rollback()
            # 可能需要从COS删除已上传的文件
            logger.error(f"数据库操作失败: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"数据库操作失败: {str(db_error)}")
    except Exception as e:
        # 确保在任何情况下都回滚事务
        try:
            db.rollback()
        except:
            pass
        logger.error(f"文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")

@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str, db: Session = Depends(get_db)):
    """获取文档处理状态"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 计算进度
    progress = 0
    if document.status == "pending":
        progress = 0
    elif document.status == "processing":
        # 基于处理时间估算进度
        if hasattr(document, 'process_start_time') and document.process_start_time:
            elapsed = (datetime.now() - document.process_start_time).total_seconds()
            progress = min(int(elapsed / 60 * 100), 90)  # 假设平均处理时间1分钟
        else:
            progress = 50
    elif document.status == "completed":
        progress = 100
    elif document.status == "failed":
        progress = 0
    
    return DocumentStatusResponse(
        document_id=document_id,
        status=document.status,
        progress=progress,
        message=f"文档状态: {document.status}",
        error_message=getattr(document, 'error_message', None)
    )

@router.get("/{document_id}", response_model=DocumentInfo)
async def get_document_info(document_id: str, db: Session = Depends(get_db)):
    """获取文档详细信息"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    from app.schemas import FileType
    
    return DocumentInfo(
        document_id=document.id,
        filename=document.filename,
        file_size=document.file_size,
        file_md5=document.file_md5,
        pages=document.pages,
        upload_time=document.upload_time,
        status=TaskStatus(document.status),
        file_type=FileType(document.file_type) if document.file_type else None,
        chunk_count=document.chunk_count,
        retry_count=document.retry_count,
        max_retries=document.max_retries
    )

@router.get("", response_model=List[DocumentInfo])
async def list_documents(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """获取文档列表"""
    documents = db.query(Document).offset(skip).limit(limit).all()
    
    from app.schemas import FileType
    
    return [
        DocumentInfo(
            document_id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size,
            file_md5=doc.file_md5,
            pages=doc.pages,
            upload_time=doc.upload_time,
            status=TaskStatus(doc.status),
            file_type=FileType(doc.file_type) if doc.file_type else None,
            chunk_count=doc.chunk_count,
            retry_count=doc.retry_count,
            max_retries=doc.max_retries
        )
        for doc in documents
    ]

@router.delete("/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """删除文档及其相关资源"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    try:
        # 删除向量存储中的文档
        try:
            vector_store = VectorStoreManager()
            vector_store.delete_document_collection(document_id)
            logger.info(f"已删除文档 {document_id} 的向量存储集合")
        except Exception as vs_error:
            logger.error(f"删除向量存储集合失败: {str(vs_error)}")
        
        # 删除存储的文件
        try:
            file_storage_manager.delete_file(
                document_id=document_id,
                storage_type=document.storage_type,
                file_path=document.file_path,
                cos_object_key=document.cos_object_key
            )
            logger.info(f"已删除文档 {document_id} 的存储文件")
        except Exception as fs_error:
            logger.error(f"删除存储文件失败: {str(fs_error)}")
        
        # 删除数据库记录
        db.delete(document)
        db.commit()
        logger.info(f"已删除文档 {document_id} 的数据库记录")
        
        return {"message": f"文档 {document_id} 已成功删除"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")

@router.get("/{document_id}/download")
async def download_document(document_id: str, db: Session = Depends(get_db)):
    """下载文档 - 返回下载链接"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    try:
        # 获取文件下载URL
        from app.utils.download_manager import download_manager
        download_info = download_manager.get_download_url(
            document_id=document_id,
            storage_type=document.storage_type,
            file_path=document.file_path,
            cos_object_key=document.cos_object_key,
            filename=document.filename
        )
        
        if not download_info["success"]:
            raise HTTPException(status_code=500, detail=download_info["error"])
        
        return {
            "document_id": document_id,
            "filename": document.filename,
            "download_url": download_info["download_url"],
            "expires": download_info.get("expires"),
            "storage_type": document.storage_type
        }
    except Exception as e:
        logger.error(f"获取文档下载链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取下载链接失败: {str(e)}")

@router.post("/check-duplicate", response_model=DuplicateCheckResponse)
async def check_duplicate_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """检查文档是否重复（基于MD5）"""
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 验证文件类型
        from app.core.document_processor import DocumentProcessor
        doc_processor = DocumentProcessor()
        
        if not doc_processor.is_supported_file(file.filename):
            supported_types = list(doc_processor.SUPPORTED_TYPES.keys())
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型。支持的类型: {', '.join(supported_types)}"
            )
        
        # 计算MD5
        file_md5 = calculate_content_md5(file_content)
        logger.info(f"文件 {file.filename} MD5: {file_md5}")
        
        # 检查是否存在重复文件
        existing_doc_id = is_duplicate_file(db, file_md5)
        
        if existing_doc_id:
            # 获取已存在的文档信息
            existing_doc = db.query(Document).filter(Document.id == existing_doc_id).first()
            
            return DuplicateCheckResponse(
                is_duplicate=True,
                existing_document_id=existing_doc_id,
                message=f"文件已存在，文档ID: {existing_doc_id}, 状态: {existing_doc.status}"
            )
        else:
            return DuplicateCheckResponse(
                is_duplicate=False,
                message="文件不存在，可以上传"
            )
    except Exception as e:
        logger.error(f"检查文件重复性失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查文件重复性失败: {str(e)}") 