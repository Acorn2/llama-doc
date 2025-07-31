"""
知识库相关的API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db, KnowledgeBase, Document, User
from app.schemas import (
    KnowledgeBaseCreate, 
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    PublicKnowledgeBaseListRequest,
    KnowledgeBaseLikeResponse,
    KnowledgeBaseAccessLogRequest,
    DocumentAddResponse,
    DocumentInfo,
    TaskStatus,
    FileType,
    ActivityType
)
from app.services.knowledge_base_service import KnowledgeBaseManager
from app.core.dependencies import get_current_user, get_optional_current_user

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    prefix="/knowledge-bases",
    tags=["knowledge_bases"],
    responses={404: {"description": "Not found"}},
)

# 创建知识库管理器实例
kb_manager = KnowledgeBaseManager()

@router.post("/", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    request_data: KnowledgeBaseCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建知识库"""
    try:
        kb = kb_manager.create_knowledge_base(
            db=db,
            kb_data=request_data,
            user_id=current_user.id
        )
        
        # 记录知识库创建活动
        from app.utils.activity_logger import log_user_activity
        from app.schemas import ActivityType
        log_user_activity(
            db=db,
            user=current_user,
            activity_type=ActivityType.KB_CREATE,
            description=f"创建知识库: {kb.name}",
            request=request,
            resource_type="knowledge_base",
            resource_id=kb.id,
            metadata={
                "name": kb.name,
                "is_public": kb.is_public,
                "description": kb.description
            }
        )
        
        # 解析标签
        tags = []
        if kb.tags:
            import json
            try:
                tags = json.loads(kb.tags)
            except json.JSONDecodeError:
                tags = []
        
        return KnowledgeBaseResponse(
            id=kb.id,
            user_id=kb.user_id,
            name=kb.name,
            description=kb.description,
            create_time=kb.create_time,
            update_time=kb.update_time,
            document_count=kb.document_count,
            status=kb.status,
            is_public=kb.is_public,
            public_description=kb.public_description,
            tags=tags,
            view_count=kb.view_count,
            like_count=kb.like_count,
            is_owner=True
        )
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    include_public: bool = Query(True, description="是否包含公开知识库"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户可访问的知识库列表"""
    try:
        knowledge_bases = kb_manager.get_accessible_knowledge_bases(
            db=db,
            user_id=current_user.id,
            include_public=include_public
        )
        
        kb_responses = []
        for kb in knowledge_bases:
            # 解析标签
            tags = []
            if kb.tags:
                import json
                try:
                    tags = json.loads(kb.tags)
                except json.JSONDecodeError:
                    tags = []
            
            kb_responses.append(KnowledgeBaseResponse(
                id=kb.id,
                user_id=kb.user_id,
                name=kb.name,
                description=kb.description,
                create_time=kb.create_time,
                update_time=kb.update_time,
                document_count=kb.document_count,
                status=kb.status,
                is_public=kb.is_public,
                public_description=kb.public_description,
                tags=tags,
                view_count=kb.view_count,
                like_count=kb.like_count,
                is_owner=kb.user_id == current_user.id
            ))
        
        return KnowledgeBaseListResponse(
            items=kb_responses,
            total=len(kb_responses)
        )
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取知识库列表失败")

@router.get("/public")
async def list_public_knowledge_bases(
    search: Optional[str] = Query(None, description="搜索关键词"),
    tags: Optional[List[str]] = Query(None, description="标签过滤"),
    sort_by: str = Query("create_time", description="排序字段"),
    sort_order: str = Query("desc", description="排序顺序"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """获取公开知识库列表"""
    try:
        request = PublicKnowledgeBaseListRequest(
            search=search,
            tags=tags,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        
        result = kb_manager.get_public_knowledge_bases(
            db=db,
            request=request,
            current_user_id=current_user.id if current_user else None
        )
        
        return {
            "success": True,
            "message": "获取公开知识库列表成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取公开知识库列表失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取公开知识库列表失败")

@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取知识库详细信息"""
    try:
        # 获取知识库信息
        kb = kb_manager.get_knowledge_base(db=db, kb_id=kb_id)
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
        
        # 检查权限：知识库创建者或公开知识库
        if kb.user_id != current_user.id and not kb.is_public:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限访问此知识库")
        
        # 记录知识库查看活动
        from app.utils.activity_logger import log_user_activity
        log_user_activity(
            db=db,
            user=current_user,
            activity_type=ActivityType.KB_VIEW,
            description=f"查看知识库详情: {kb.name}",
            request=request,
            resource_type="knowledge_base",
            resource_id=kb_id,
            metadata={
                "kb_name": kb.name,
                "is_public": kb.is_public,
                "document_count": kb.document_count
            }
        )
        
        # 解析标签
        tags = []
        if kb.tags:
            import json
            try:
                tags = json.loads(kb.tags)
            except json.JSONDecodeError:
                tags = []
        
        return KnowledgeBaseResponse(
            id=kb.id,
            user_id=kb.user_id,
            name=kb.name,
            description=kb.description,
            create_time=kb.create_time,
            update_time=kb.update_time,
            document_count=kb.document_count,
            status=kb.status,
            is_public=kb.is_public,
            public_description=kb.public_description,
            tags=tags,
            view_count=kb.view_count,
            like_count=kb.like_count,
            is_owner=kb.user_id == current_user.id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库详情失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取知识库详情失败")

@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新知识库信息"""
    try:
        kb = kb_manager.update_knowledge_base(
            db=db,
            kb_id=kb_id,
            user_id=current_user.id,
            update_data=request
        )
        
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在或无权限访问")
        
        # 解析标签
        tags = []
        if kb.tags:
            import json
            try:
                tags = json.loads(kb.tags)
            except json.JSONDecodeError:
                tags = []
        
        return KnowledgeBaseResponse(
            id=kb.id,
            user_id=kb.user_id,
            name=kb.name,
            description=kb.description,
            create_time=kb.create_time,
            update_time=kb.update_time,
            document_count=kb.document_count,
            status=kb.status,
            is_public=kb.is_public,
            public_description=kb.public_description,
            tags=tags,
            view_count=kb.view_count,
            like_count=kb.like_count,
            is_owner=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新知识库失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除知识库"""
    try:
        # 检查知识库是否存在且用户有权限
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.user_id == current_user.id
        ).first()
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在或无权限访问")
        
        # 执行删除
        success = kb_manager.delete_knowledge_base(db=db, kb_id=kb_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除知识库失败")
        
        # 记录删除活动
        from app.utils.activity_logger import log_user_activity
        log_user_activity(
            db=db,
            user=current_user,
            activity_type=ActivityType.KB_DELETE,
            description=f"删除知识库: {kb.name}",
            request=request,
            resource_type="knowledge_base",
            resource_id=kb_id,
            metadata={
                "kb_name": kb.name,
                "document_count": kb.document_count
            }
        )
        
        return {
            "success": True,
            "message": "知识库删除成功",
            "data": {
                "kb_id": kb_id,
                "kb_name": kb.name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除知识库失败")

@router.post("/{kb_id}/like", response_model=KnowledgeBaseLikeResponse)
async def toggle_knowledge_base_like(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """切换知识库点赞状态"""
    try:
        result = kb_manager.toggle_knowledge_base_like(
            db=db,
            kb_id=kb_id,
            user_id=current_user.id
        )
        
        return KnowledgeBaseLikeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"切换点赞状态失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="操作失败")

@router.post("/{kb_id}/access")
async def log_knowledge_base_access(
    kb_id: str,
    request: KnowledgeBaseAccessLogRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """记录知识库访问"""
    try:
        kb_manager.record_knowledge_base_access(
            db=db,
            kb_id=kb_id,
            user_id=current_user.id,
            access_type=request.access_type,
            metadata=request.access_metadata
        )
        
        return {"success": True, "message": "访问记录成功"}
    except Exception as e:
        logger.error(f"记录访问失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="记录访问失败")

@router.get("/{kb_id}/documents")
async def list_knowledge_base_documents(
    kb_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取知识库中的文档列表"""
    try:
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
        
        # 检查权限：知识库创建者或公开知识库
        if kb.user_id != current_user.id and not kb.is_public:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限访问此知识库")
        
        # 获取知识库中的文档列表
        documents = kb_manager.list_kb_documents(db=db, kb_id=kb_id)
        
        # 记录知识库访问活动
        from app.utils.activity_logger import log_user_activity
        log_user_activity(
            db=db,
            user=current_user,
            activity_type=ActivityType.KB_VIEW,
            description=f"查看知识库文档列表: {kb.name}",
            request=request,
            resource_type="knowledge_base",
            resource_id=kb_id,
            metadata={
                "kb_name": kb.name,
                "document_count": len(documents)
            }
        )
        
        # 转换为响应格式
        document_responses = []
        for doc in documents:
            document_responses.append(DocumentInfo(
                document_id=doc.id,
                filename=doc.filename,
                file_size=doc.file_size,
                file_md5=doc.file_md5,
                pages=doc.pages or 0,
                upload_time=doc.upload_time,
                status=TaskStatus(doc.status),
                file_type=FileType(doc.file_type) if doc.file_type else None,
                chunk_count=doc.chunk_count,
                retry_count=doc.retry_count
            ))
        
        return {
            "success": True,
            "message": "获取知识库文档列表成功",
            "data": {
                "kb_id": kb_id,
                "kb_name": kb.name,
                "documents": document_responses,
                "total": len(document_responses)
            }
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"获取知识库文档列表失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取文档列表失败")

@router.post("/{kb_id}/documents/{document_id}")
async def add_document_to_knowledge_base(
    kb_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加文档到知识库（仅建立数据库关联，向量复制由定时任务处理）"""
    try:
        # 检查知识库权限：只有创建者可以添加文档
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.user_id == current_user.id
        ).first()
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在或无权限访问")
        
        # 检查文档权限：只能添加自己的文档
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在或无权限访问")
        
        # 仅添加数据库关联记录，不处理向量复制
        kb_doc = kb_manager.add_document_to_kb_db_only(
            db=db,
            kb_id=kb_id,
            document_id=document_id
        )
        
        if kb_doc is None:
            return {
                "success": True,
                "message": "文档已在知识库中",
                "data": {
                    "kb_id": kb_id,
                    "document_id": document_id,
                    "already_exists": True,
                    "vector_status": "pending"
                }
            }
        
        return {
            "success": True,
            "message": "文档已添加到知识库，向量数据将由后台任务处理",
            "data": {
                "kb_id": kb_id,
                "document_id": document_id,
                "relation_id": kb_doc.id,
                "add_time": kb_doc.add_time,
                "vector_status": "pending"
            }
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"添加文档到知识库失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="添加文档失败")

@router.delete("/{kb_id}/documents/{document_id}")
async def remove_document_from_knowledge_base(
    kb_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """从知识库移除文档"""
    try:
        # 检查知识库权限：只有创建者可以移除文档
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.user_id == current_user.id
        ).first()
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在或无权限访问")
        
        # 移除文档
        success = kb_manager.remove_document_from_kb(
            db=db,
            kb_id=kb_id,
            document_id=document_id
        )
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不在知识库中")
        
        return {
            "success": True,
            "message": "文档从知识库移除成功",
            "data": {
                "kb_id": kb_id,
                "document_id": document_id
            }
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"从知识库移除文档失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="移除文档失败")

@router.get("/{kb_id}/documents/{document_id}/vector-status")
async def get_document_vector_status(
    kb_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文档在知识库中的向量同步状态"""
    try:
        # 检查知识库权限
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id
        ).first()
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
        
        # 检查权限：知识库创建者或公开知识库
        if kb.user_id != current_user.id and not kb.is_public:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限访问此知识库")
        
        # 查找关联记录
        from app.database import KnowledgeBaseDocument
        kb_doc = db.query(KnowledgeBaseDocument).filter(
            KnowledgeBaseDocument.kb_id == kb_id,
            KnowledgeBaseDocument.document_id == document_id
        ).first()
        
        if not kb_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不在知识库中")
        
        return {
            "success": True,
            "data": {
                "kb_id": kb_id,
                "document_id": document_id,
                "vector_sync_status": kb_doc.vector_sync_status,
                "vector_sync_time": kb_doc.vector_sync_time,
                "vector_sync_error": kb_doc.vector_sync_error,
                "add_time": kb_doc.add_time
            },
            "message": "获取向量同步状态成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取向量同步状态失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取状态失败")

@router.get("/vector-sync/stats")
async def get_vector_sync_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取向量同步统计信息（仅超级用户）"""
    try:
        if not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要超级用户权限")
        
        from app.services.vector_sync_service import vector_sync_processor
        stats = vector_sync_processor.get_sync_status(db)
        
        return {
            "success": True,
            "data": stats,
            "message": "获取向量同步统计成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取向量同步统计失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取统计失败") 