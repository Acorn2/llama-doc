"""
LlamaIndex API路由
"""
import os
import logging
import tempfile
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.database import get_db, Document as DBDocument
from app.schemas import (
    DocumentResponse, DocumentInfo, DocumentStatus, 
    LlamaIndexQueryRequest, LlamaIndexQueryResponse
)
from app.llamaindex.adapter import LlamaIndexAdapter
from app.utils.file_utils import save_upload_file_temp

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    tags=["llamaindex"],
    responses={404: {"description": "Not found"}},
)

# 创建LlamaIndex适配器
llamaindex_adapter = LlamaIndexAdapter(
    embedding_model_name="text-embedding-v1",  # 默认使用通义千问嵌入模型
    llm_model_name="qwen-max",  # 默认使用通义千问LLM
    chunk_size=512,
    chunk_overlap=50,
    similarity_top_k=3
)

@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(None),
    user_id: str = Form("system"),
    db: Session = Depends(get_db)
):
    """
    上传文档并使用LlamaIndex处理
    """
    logger.info(f"接收到文档上传请求: {file.filename}")
    
    # 保存上传的文件到临时目录
    temp_file_path = await save_upload_file_temp(file)
    
    try:
        # 如果没有提供标题，则使用文件名
        if not title:
            title = file.filename
        
        # 上传并处理文档
        document_id = llamaindex_adapter.upload_and_process_document(
            file_path=temp_file_path,
            file_name=title,
            user_id=user_id,
            db=db
        )
        
        if not document_id:
            raise HTTPException(status_code=500, detail="文档处理失败")
        
        # 获取文档记录
        db_document = db.query(DBDocument).filter(DBDocument.id == document_id).first()
        
        # 返回文档信息
        return DocumentInfo(
            document_id=db_document.id,
            filename=db_document.filename,
            file_size=db_document.file_size,
            file_md5=db_document.file_md5,
            pages=db_document.pages or 0,
            upload_time=db_document.upload_time,
            status=DocumentStatus(db_document.status),
            chunk_count=db_document.chunk_count,
            retry_count=db_document.retry_count,
            max_retries=db_document.max_retries
        )
    finally:
        # 删除临时文件
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.post("/query", response_model=LlamaIndexQueryResponse)
async def query_document(
    request: LlamaIndexQueryRequest,
    db: Session = Depends(get_db)
):
    """
    使用LlamaIndex查询文档
    """
    logger.info(f"接收到文档查询请求: {request.query}, 文档ID: {request.document_id}")
    
    # 查询文档
    answer, source_nodes = llamaindex_adapter.query_document(
        document_id=request.document_id,
        query_text=request.query,
        similarity_top_k=request.similarity_top_k,
        similarity_cutoff=request.similarity_cutoff,
        db=db
    )
    
    # 返回查询结果
    return LlamaIndexQueryResponse(
        answer=answer,
        source_nodes=source_nodes
    )

@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents(
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    列出文档
    """
    # 构建查询
    query = db.query(DBDocument)
    
    # 如果提供了用户ID，则按用户ID过滤
    if user_id:
        query = query.filter(DBDocument.user_id == user_id)
    
    # 获取文档列表
    documents = query.offset(skip).limit(limit).all()
    
    # 返回文档列表
    return [
        DocumentInfo(
            document_id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size,
            file_md5=doc.file_md5,
            pages=doc.pages or 0,
            upload_time=doc.upload_time,
            status=DocumentStatus(doc.status),
            chunk_count=doc.chunk_count,
            retry_count=doc.retry_count,
            max_retries=doc.max_retries
        )
        for doc in documents
    ] 