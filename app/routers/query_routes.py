"""
查询相关的API路由
"""
import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, Document, QueryHistory
from app.schemas import QueryRequest, QueryResponse
from app.core.vector_store import VectorStoreManager
from app.core.enhanced_vector_store import EnhancedVectorStore
from app.core.agent_core import DocumentAnalysisAgent
from app.core.cache_manager import cache_manager

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    prefix="/queries",
    tags=["queries"],
    responses={404: {"description": "Not found"}},
)

# 创建向量存储管理器和智能体实例
vector_store = VectorStoreManager()
enhanced_vector_store = EnhancedVectorStore()
agent = DocumentAnalysisAgent(vector_store_manager=vector_store)

@router.post("/documents/{document_id}/query", response_model=QueryResponse)
async def query_document(
    document_id: str,
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """查询文档内容"""
    
    # 检查文档状态
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.status != "completed":
        raise HTTPException(status_code=400, detail=f"文档状态: {document.status}，无法查询")
    
    try:
        start_time = time.time()
        
        # 从向量存储中检索相关文本块
        search_results = vector_store.search_document(
            document_id=document_id,
            query=request.question,
            k=request.max_results
        )
        
        if not search_results:
            return QueryResponse(
                answer="抱歉，在该文档中未找到与您问题相关的内容。",
                confidence=0.0,
                sources=[],
                processing_time=time.time() - start_time
            )
        
        # 使用智能体生成回答
        response = agent.answer_question(
            document_id=document_id,
            question=request.question,
            search_results=search_results
        )
        
        processing_time = time.time() - start_time
        
        # 记录查询历史
        query_history = QueryHistory(
            document_id=document_id,
            question=request.question,
            answer=response["answer"],
            confidence=response["confidence"],
            processing_time=processing_time
        )
        db.add(query_history)
        db.commit()
        
        return QueryResponse(
            answer=response["answer"],
            confidence=response["confidence"],
            sources=response["sources"],
            processing_time=processing_time
        )
    except Exception as e:
        logger.error(f"查询文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询文档失败: {str(e)}")

@router.post("/documents/{document_id}/hybrid-query", response_model=QueryResponse)
async def hybrid_query_document(
    document_id: str,
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """混合检索查询文档内容"""
    
    # 检查文档状态
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.status != "completed":
        raise HTTPException(status_code=400, detail=f"文档状态: {document.status}，无法查询")
    
    try:
        start_time = time.time()
        
        # 使用混合检索
        search_results = vector_store.hybrid_search(
            document_id=document_id,
            query=request.question,
            k=request.max_results,
            alpha=0.7  # 向量搜索权重
        )
        
        if not search_results:
            return QueryResponse(
                answer="抱歉，在该文档中未找到与您问题相关的内容。",
                confidence=0.0,
                sources=[],
                processing_time=time.time() - start_time
            )
        
        # 使用智能体生成回答
        response = agent.answer_question(
            document_id=document_id,
            question=request.question,
            search_results=search_results
        )
        
        processing_time = time.time() - start_time
        
        # 记录查询历史
        query_history = QueryHistory(
            document_id=document_id,
            question=request.question,
            answer=response["answer"],
            confidence=response["confidence"],
            processing_time=processing_time
        )
        db.add(query_history)
        db.commit()
        
        return QueryResponse(
            answer=response["answer"],
            confidence=response["confidence"],
            sources=response["sources"],
            processing_time=processing_time
        )
    except Exception as e:
        logger.error(f"混合查询文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"混合查询文档失败: {str(e)}")

@router.post("/documents/{document_id}/enhanced-query", response_model=QueryResponse)
async def enhanced_query_document(
    document_id: str,
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """增强检索查询文档内容"""
    
    # 检查文档状态
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.status != "completed":
        raise HTTPException(status_code=400, detail=f"文档状态: {document.status}，无法查询")
    
    try:
        start_time = time.time()
        
        # 使用缓存检查是否有缓存的结果
        cache_key = f"enhanced_query:{document_id}:{request.question}"
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            logger.info(f"使用缓存的增强查询结果: {cache_key}")
            return QueryResponse(
                answer=cached_result["answer"],
                confidence=cached_result["confidence"],
                sources=cached_result["sources"],
                processing_time=cached_result["processing_time"]
            )
        
        # 使用增强向量存储进行检索
        search_results = enhanced_vector_store.search(
            document_id=document_id,
            query=request.question,
            k=request.max_results
        )
        
        if not search_results:
            return QueryResponse(
                answer="抱歉，在该文档中未找到与您问题相关的内容。",
                confidence=0.0,
                sources=[],
                processing_time=time.time() - start_time
            )
        
        # 使用智能体生成回答
        response = agent.answer_question(
            document_id=document_id,
            question=request.question,
            search_results=search_results,
            use_enhanced_prompt=True
        )
        
        processing_time = time.time() - start_time
        
        # 记录查询历史
        query_history = QueryHistory(
            document_id=document_id,
            question=request.question,
            answer=response["answer"],
            confidence=response["confidence"],
            processing_time=processing_time
        )
        db.add(query_history)
        db.commit()
        
        # 缓存结果
        cache_data = {
            "answer": response["answer"],
            "confidence": response["confidence"],
            "sources": response["sources"],
            "processing_time": processing_time
        }
        cache_manager.set(cache_key, cache_data, ttl=3600)  # 缓存1小时
        
        return QueryResponse(
            answer=response["answer"],
            confidence=response["confidence"],
            sources=response["sources"],
            processing_time=processing_time
        )
    except Exception as e:
        logger.error(f"增强查询文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"增强查询文档失败: {str(e)}")

@router.post("/documents/{document_id}/summary")
async def generate_document_summary(document_id: str, db: Session = Depends(get_db)):
    """生成文档摘要"""
    
    # 检查文档状态
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.status != "completed":
        raise HTTPException(status_code=400, detail=f"文档状态: {document.status}，无法生成摘要")
    
    try:
        # 使用缓存检查是否有缓存的摘要
        cache_key = f"summary:{document_id}"
        cached_summary = cache_manager.get(cache_key)
        
        if cached_summary:
            logger.info(f"使用缓存的文档摘要: {cache_key}")
            return cached_summary
        
        # 生成摘要
        summary = agent.generate_document_summary(document_id)
        
        # 缓存摘要
        cache_manager.set(cache_key, summary, ttl=86400)  # 缓存24小时
        
        return summary
    except Exception as e:
        logger.error(f"生成文档摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成文档摘要失败: {str(e)}")

@router.post("/documents/{document_id}/enhanced-summary")
async def generate_enhanced_document_summary(document_id: str, db: Session = Depends(get_db)):
    """生成增强文档摘要"""
    
    # 检查文档状态
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.status != "completed":
        raise HTTPException(status_code=400, detail=f"文档状态: {document.status}，无法生成摘要")
    
    try:
        # 使用缓存检查是否有缓存的增强摘要
        cache_key = f"enhanced_summary:{document_id}"
        cached_summary = cache_manager.get(cache_key)
        
        if cached_summary:
            logger.info(f"使用缓存的增强文档摘要: {cache_key}")
            return cached_summary
        
        # 生成增强摘要
        summary = agent.generate_enhanced_document_summary(document_id)
        
        # 缓存摘要
        cache_manager.set(cache_key, summary, ttl=86400)  # 缓存24小时
        
        return summary
    except Exception as e:
        logger.error(f"生成增强文档摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成增强文档摘要失败: {str(e)}") 