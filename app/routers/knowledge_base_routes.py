"""
知识库相关的API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    DocumentAddResponse
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
    request: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建知识库"""
    try:
        kb = kb_manager.create_knowledge_base(
            db=db,
            kb_data=request,
            user_id=current_user.id
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