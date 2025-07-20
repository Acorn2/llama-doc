"""
知识库相关的API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db, KnowledgeBase, Document
from app.schemas import (
    KnowledgeBaseCreate, 
    DocumentAddResponse
)
from app.schemas.__init__ import (
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse
)
from app.services.knowledge_base_service import KnowledgeBaseManager

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

@router.post("/", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    request: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """创建知识库"""
    try:
        kb = kb_manager.create_knowledge_base(
            db=db,
            name=request.name,
            description=request.description
        )
        
        # 转换为响应模型
        from app.schemas.__init__ import KnowledgeBaseInfo
        
        kb_info = KnowledgeBaseInfo(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            document_count=getattr(kb, 'document_count', 0),
            created_at=kb.create_time,
            updated_at=kb.update_time or kb.create_time,
            embedding_model=getattr(kb, 'embedding_model', None)
        )
        
        return KnowledgeBaseResponse(
            success=True,
            message="知识库创建成功",
            knowledge_base=kb_info
        )
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建知识库失败: {str(e)}")

@router.get("/", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = "active",
    db: Session = Depends(get_db)
):
    """列出所有知识库"""
    try:
        result = kb_manager.list_knowledge_bases(
            db=db,
            skip=skip,
            limit=limit,
            status=status
        )
        
        # 转换为响应模型
        from app.schemas.__init__ import KnowledgeBaseInfo, KnowledgeBaseList
        
        kb_infos = []
        for kb in result["items"]:
            kb_info = KnowledgeBaseInfo(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                document_count=getattr(kb, 'document_count', 0),
                created_at=kb.create_time,
                updated_at=kb.update_time or kb.create_time,
                embedding_model=getattr(kb, 'embedding_model', None)
            )
            kb_infos.append(kb_info)
        
        kb_list = KnowledgeBaseList(
            knowledge_bases=kb_infos,
            total=result["total"]
        )
        
        return KnowledgeBaseListResponse(
            success=True,
            data=kb_list,
            message="获取知识库列表成功"
        )
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取知识库列表失败: {str(e)}")

@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """获取知识库详情"""
    kb = kb_manager.get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    # 转换为响应模型
    from app.schemas.__init__ import KnowledgeBaseInfo
    
    kb_info = KnowledgeBaseInfo(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=getattr(kb, 'document_count', 0),
        created_at=kb.create_time,
        updated_at=kb.update_time or kb.create_time,
        embedding_model=getattr(kb, 'embedding_model', None)
    )
    
    return KnowledgeBaseResponse(
        success=True,
        message="获取知识库详情成功",
        knowledge_base=kb_info
    )

@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """更新知识库"""
    kb = kb_manager.update_knowledge_base(
        db=db,
        kb_id=kb_id,
        name=request.name,
        description=request.description
    )
    
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    # 转换为响应模型
    from app.schemas.__init__ import KnowledgeBaseInfo
    
    kb_info = KnowledgeBaseInfo(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        document_count=getattr(kb, 'document_count', 0),
        created_at=kb.create_time,
        updated_at=kb.update_time or kb.create_time,
        embedding_model=getattr(kb, 'embedding_model', None)
    )
    
    return KnowledgeBaseResponse(
        success=True,
        message="知识库更新成功",
        knowledge_base=kb_info
    )

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """删除知识库（逻辑删除）"""
    success = kb_manager.delete_knowledge_base(db, kb_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    return {"success": True, "message": "知识库已删除"}

@router.post("/{kb_id}/documents/{document_id}", response_model=DocumentAddResponse)
async def add_document_to_kb(
    kb_id: str,
    document_id: str,
    db: Session = Depends(get_db)
):
    """添加文档到知识库"""
    try:
        kb_doc = kb_manager.add_document_to_kb(db, kb_id, document_id)
        
        # 如果返回None，说明文档已在知识库中
        if kb_doc is None:
            return DocumentAddResponse(
                success=True,
                message="文档已在知识库中",
                kb_id=kb_id,
                document_id=document_id
            )
        
        return DocumentAddResponse(
            success=True,
            message="文档成功添加到知识库",
            kb_id=kb_id,
            document_id=document_id
        )
    except ValueError as e:
        logger.error(f"添加文档到知识库失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"添加文档到知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加文档到知识库失败: {str(e)}")

@router.delete("/{kb_id}/documents/{document_id}")
async def remove_document_from_kb(
    kb_id: str,
    document_id: str,
    db: Session = Depends(get_db)
):
    """从知识库移除文档"""
    try:
        success = kb_manager.remove_document_from_kb(db, kb_id, document_id)
        
        if not success:
            return {"success": False, "message": "文档不在知识库中"}
        
        return {"success": True, "message": "文档已从知识库移除"}
    except ValueError as e:
        logger.error(f"从知识库移除文档失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"从知识库移除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"从知识库移除文档失败: {str(e)}")

@router.get("/{kb_id}/documents")
async def list_kb_documents(
    kb_id: str,
    db: Session = Depends(get_db)
):
    """列出知识库中的所有文档"""
    try:
        documents = kb_manager.list_kb_documents(db, kb_id)
        
        # 格式化输出
        result = []
        for doc in documents:
            result.append({
                "id": doc.id,
                "filename": doc.filename,
                "pages": doc.pages,
                "upload_time": doc.upload_time,
                "status": doc.status
            })
        
        return {"items": result, "total": len(result)}
    except ValueError as e:
        logger.error(f"获取知识库文档列表失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取知识库文档列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取知识库文档列表失败: {str(e)}")

@router.post("/{kb_id}/search")
async def search_knowledge_base(
    kb_id: str,
    query: str = Query(..., description="搜索查询"),
    top_k: int = Query(5, description="返回结果数量"),
    db: Session = Depends(get_db)
):
    """搜索知识库内容"""
    try:
        results = kb_manager.search_knowledge_base(
            kb_id=kb_id,
            query=query,
            top_k=top_k,
            db=db
        )
        
        return {"results": results, "total": len(results)}
    except ValueError as e:
        logger.error(f"搜索知识库失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"搜索知识库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索知识库失败: {str(e)}") 