# 禁用 ChromaDB 遥测功能，避免遥测错误
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import uuid
import asyncio
from datetime import datetime, timedelta
import logging
import time
from typing import Set, List

from .database import get_db, create_tables, Document, QueryHistory
from .schemas import *
from .core.document_processor import DocumentProcessor
from .core.vector_store import VectorStoreManager
from .core.agent_core import DocumentAnalysisAgent
from .core.model_factory import ModelFactory
from .logging_config import setup_logging, RequestLoggingMiddleware
from .core.enhanced_vector_store import EnhancedVectorStore
from .core.cache_manager import cache_manager
from .utils.file_utils import calculate_content_md5, is_duplicate_file
from .utils.file_storage import file_storage_manager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 文档处理器类
class DocumentTaskProcessor:
    """定时任务文档处理器"""
    
    def __init__(self):
        self.processing: Set[str] = set()  # 正在处理的文档ID
        self.is_running = False
        self.poll_interval = 10  # 轮询间隔（秒）
        self.retry_interval = 300  # 重试间隔（5分钟）
        
    async def start_polling(self):
        """启动定时轮询"""
        self.is_running = True
        logger.info("文档处理轮询已启动")
        
        while self.is_running:
            try:
                await self.process_pending_documents()
                await self.process_failed_documents()  # 新增：处理失败的文档
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"轮询处理失败: {e}")
                await asyncio.sleep(self.poll_interval)
    
    def stop_polling(self):
        """停止轮询"""
        self.is_running = False
        logger.info("文档处理轮询已停止")
    
    async def process_pending_documents(self):
        """处理待处理的文档"""
        from .database import SessionLocal
        
        db = SessionLocal()
        try:
            # 查询待处理的文档（避免重复处理）
            pending_docs = db.query(Document).filter(
                Document.status == "pending"
            ).limit(5).all()  # 限制并发数
            
            if pending_docs:
                logger.info(f"发现 {len(pending_docs)} 个待处理文档")
                
                for doc in pending_docs:
                    if doc.id not in self.processing:
                        # 标记为正在处理
                        self.processing.add(doc.id)
                        doc.status = "processing"
                        doc.process_start_time = datetime.now()
                        db.commit()
                        
                        # 异步处理文档
                        asyncio.create_task(self.process_single_document(doc.id, doc.file_path))
                        
        except Exception as e:
            logger.error(f"查询待处理文档失败: {e}")
        finally:
            db.close()
    
    async def process_failed_documents(self):
        """处理失败的文档（重试逻辑）"""
        from .database import SessionLocal
        
        db = SessionLocal()
        try:
            # 查询需要重试的失败文档
            # 条件：状态为failed、重试次数小于最大重试次数、距离上次重试超过指定时间间隔
            retry_time_threshold = datetime.now() - timedelta(seconds=self.retry_interval)
            
            failed_docs = db.query(Document).filter(
                Document.status == "failed",
                Document.retry_count < Document.max_retries,
                # 首次失败或者距离上次重试已过指定时间
                (Document.last_retry_time.is_(None)) | (Document.last_retry_time < retry_time_threshold)
            ).limit(3).all()  # 限制重试并发数
            
            if failed_docs:
                logger.info(f"发现 {len(failed_docs)} 个需要重试的失败文档")
                
                for doc in failed_docs:
                    if doc.id not in self.processing:
                        # 标记为正在重试
                        self.processing.add(doc.id)
                        doc.status = "processing"
                        doc.retry_count += 1
                        doc.last_retry_time = datetime.now()
                        doc.process_start_time = datetime.now()
                        db.commit()
                        
                        logger.info(f"开始重试文档 {doc.id}，第 {doc.retry_count} 次重试")
                        
                        # 异步处理文档
                        asyncio.create_task(self.process_single_document(
                            doc.id, doc.file_path, is_retry=True
                        ))
                        
        except Exception as e:
            logger.error(f"查询重试文档失败: {e}")
        finally:
            db.close()
    
    async def process_single_document(self, document_id: str, file_path: str, is_retry: bool = False):
        """处理单个文档 - 支持COS存储"""
        from .database import SessionLocal
        
        db = SessionLocal()
        try:
            if is_retry:
                logger.info(f"开始重试处理文档: {document_id}")
            else:
                logger.info(f"开始处理文档: {document_id}")
            
            # 获取文档信息
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"文档不存在: {document_id}")
                return
            
            # 获取处理组件
            processor = DocumentProcessor()
            
            # 根据环境变量选择模型类型
            embedding_type = os.getenv("EMBEDDING_TYPE", "qwen")
            vector_store = VectorStoreManager(
                embedding_type=embedding_type,
                embedding_config={
                    "model": os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v1")
                }
            )
            
            # 处理文档 - 支持COS存储
            result = processor.process_document(
                document_id=document_id,
                storage_type=document.storage_type,
                file_path=document.file_path,
                cos_object_key=document.cos_object_key
            )
            
            if result["success"]:
                # 创建向量存储
                vector_store.create_document_collection(document_id)
                vector_store.add_document_chunks(document_id, result["chunks"])
                
                # 更新数据库状态
                document.status = "completed"
                document.pages = result["metadata"]["pages"]
                document.chunk_count = result["chunk_count"]
                document.process_end_time = datetime.now()
                # 成功后清空错误信息
                document.error_message = None
                db.commit()
                
                if is_retry:
                    logger.info(f"文档 {document_id} 重试处理成功")
                else:
                    logger.info(f"文档 {document_id} 处理完成")
            else:
                # 处理失败
                if document.retry_count >= document.max_retries:
                    document.status = "failed_permanently"
                    error_msg = f"文档处理失败，已达最大重试次数({document.max_retries})。最后错误: {result['error']}"
                    logger.error(f"文档 {document_id} 永久失败: {error_msg}")
                else:
                    document.status = "failed"
                    error_msg = f"处理失败(第{document.retry_count}次重试): {result['error']}"
                    logger.error(f"文档 {document_id} 处理失败，将稍后重试: {result['error']}")
                
                document.error_message = error_msg
                db.commit()
                
        except Exception as e:
            # 处理异常
            error_msg = f"处理文档异常: {str(e)}"
            logger.error(f"处理文档 {document_id} 异常: {e}")
            
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                if document.retry_count >= document.max_retries:
                    document.status = "failed_permanently"
                    error_msg = f"文档处理异常，已达最大重试次数({document.max_retries})。最后错误: {str(e)}"
                else:
                    document.status = "failed"
                    error_msg = f"处理异常(第{document.retry_count}次重试): {str(e)}"
                
                document.error_message = error_msg
                db.commit()
        finally:
            # 从处理中移除
            self.processing.discard(document_id)
            db.close()

# 创建FastAPI应用
app = FastAPI(
    title="PDF文献分析智能体",
    description="基于LangChain的PDF文档问答系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保必要目录存在
os.makedirs("uploads", exist_ok=True)
os.makedirs("vector_db", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 在应用初始化时检查可用模型
available_models = ModelFactory.get_available_models()
logger.info(f"可用模型: {available_models}")

# 初始化核心组件 - 支持多模型
processor = DocumentProcessor()

# 根据环境变量选择模型类型
llm_type = os.getenv("LLM_TYPE", "qwen")
embedding_type = os.getenv("EMBEDDING_TYPE", "qwen")

logger.info(f"使用语言模型: {llm_type}")
logger.info(f"使用嵌入模型: {embedding_type}")

# 在应用初始化时添加
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir="./logs"
)

# 添加中间件
app.add_middleware(RequestLoggingMiddleware)

# 使用增强的向量存储
vector_store = EnhancedVectorStore(
    qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
    qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
    qdrant_https=os.getenv("QDRANT_HTTPS", "false").lower() == "true",
    qdrant_api_key=os.getenv("QDRANT_API_KEY"),
    embedding_type=os.getenv("EMBEDDING_TYPE", "qwen"),
    embedding_config={}
)

agent = DocumentAnalysisAgent(
    vector_store_manager=vector_store,
    llm_type=llm_type,
    model_config={
        "model": os.getenv("QWEN_MODEL", "qwen-plus"),
        "temperature": 0.1
    }
)

# 全局处理器实例
doc_processor = DocumentTaskProcessor()

# 创建数据库表
create_tables()

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化操作"""
    logger.info("PDF文献分析智能体服务启动")
    logger.info("正在初始化数据库...")
    create_tables()
    
    # 启动文档处理轮询
    asyncio.create_task(doc_processor.start_polling())

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理操作"""
    doc_processor.stop_polling()

@app.get("/api/v1/", response_model=HealthCheck)
async def root():
    """健康检查接口"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        services={
            "database": "connected",
            "vector_store": "ready",
            "llm": "ready"
        }
    )

@app.post("/api/v1/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传PDF文档 - 支持重复检测和腾讯云COS存储"""
    
    # 先读取文件内容，验证文件类型和大小
    file_content = await file.read()
    
    # 验证文件类型
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    
    # 验证文件大小（50MB限制）
    if len(file_content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过50MB")
    
    try:
        # 计算MD5等不涉及数据库的操作
        file_md5 = calculate_content_md5(file_content)
        logger.info(f"文件 {file.filename} MD5: {file_md5}")
        
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
                # COS相关字段
                cos_object_key=storage_result["cos_object_key"],
                cos_file_url=storage_result["cos_file_url"],
                cos_etag=storage_result["cos_etag"],
                storage_type=storage_result["storage_type"]
            )
            db.add(db_document)
            db.commit()
            
            storage_info = "腾讯云COS" if storage_result["storage_type"] == "cos" else "本地存储"
            logger.info(f"新文档上传成功({storage_info})，等待处理: {document_id}")
            
            return DocumentUploadResponse(
                document_id=document_id,
                filename=file.filename,
                status=TaskStatus.PENDING,
                upload_time=datetime.now(),
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

@app.get("/api/v1/documents/{document_id}/status")
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
    
    return {
        "document_id": document_id,
        "status": document.status,
        "progress": progress,
        "message": f"文档状态: {document.status}",
        "error_message": getattr(document, 'error_message', None)
    }

@app.post("/api/v1/documents/{document_id}/hybrid-query")
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
            max_results=request.max_results
        )
        
        # 记录查询历史
        query_history = QueryHistory(
            document_id=document_id,
            question=request.question,
            answer=response["answer"],
            confidence=response["confidence"],
            processing_time=response["processing_time"]
        )
        db.add(query_history)
        db.commit()
        
        return QueryResponse(**response)
        
    except Exception as e:
        logger.error(f"混合查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.post("/api/v1/documents/{document_id}/query", response_model=QueryResponse)
async def query_document(
    document_id: str,  # 从URL路径获取
    request: QueryRequest,  # 只包含question和max_results
    db: Session = Depends(get_db)
):
    """查询文档内容"""
    
    # 检查文档是否存在且已处理完成
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.status != "completed":
        raise HTTPException(status_code=400, detail=f"文档状态: {document.status}，无法查询")
    
    try:
        # 执行查询 - 使用URL中的document_id
        result = agent.answer_question(
            document_id=document_id,  # 来自URL路径
            question=request.question,  # 来自请求体
            max_results=request.max_results  # 来自请求体
        )
        
        if result["success"]:
            # 保存查询历史
            query_record = QueryHistory(
                document_id=document_id,
                question=request.question,
                answer=result["answer"],
                confidence=result["confidence"],
                processing_time=result["processing_time"]
            )
            db.add(query_record)
            db.commit()
            
            return QueryResponse(
                answer=result["answer"],
                confidence=result["confidence"],
                sources=result["sources"],
                processing_time=result["processing_time"]
            )
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}")

@app.get("/api/v1/documents/{document_id}", response_model=DocumentInfo)
async def get_document_info(document_id: str, db: Session = Depends(get_db)):
    """获取文档信息"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return DocumentInfo(
        document_id=document.id,
        filename=document.filename,
        file_size=document.file_size,
        file_md5=document.file_md5,
        pages=document.pages,
        upload_time=document.upload_time,
        status=TaskStatus(document.status),
        chunk_count=document.chunk_count,
        retry_count=document.retry_count,
        max_retries=document.max_retries
    )

@app.get("/api/v1/documents", response_model=List[DocumentInfo])
async def list_documents(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """获取文档列表"""
    
    documents = db.query(Document).offset(skip).limit(limit).all()
    
    return [
        DocumentInfo(
            document_id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size,
            file_md5=doc.file_md5,
            pages=doc.pages,
            upload_time=doc.upload_time,
            status=TaskStatus(doc.status),
            chunk_count=doc.chunk_count,
            retry_count=doc.retry_count,
            max_retries=doc.max_retries
        )
        for doc in documents
    ]

@app.post("/api/v1/documents/{document_id}/summary")
async def generate_document_summary(document_id: str, db: Session = Depends(get_db)):
    """生成文档摘要"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.status != "completed":
        raise HTTPException(status_code=400, detail=f"文档状态: {document.status}，无法生成摘要")
    
    try:
        result = agent.generate_summary(document_id)
        
        if result["success"]:
            return {"summary": result["summary"]}
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"摘要生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"摘要生成失败: {str(e)}")

@app.delete("/api/v1/documents/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """删除文档 - 支持COS和本地存储"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    try:
        # 删除文件（支持COS和本地存储）
        file_deleted = file_storage_manager.delete_file(
            document_id=document_id,
            storage_type=document.storage_type,
            file_path=document.file_path,
            cos_object_key=document.cos_object_key
        )
        
        if not file_deleted:
            logger.warning(f"文件删除失败，但继续删除数据库记录: {document_id}")
        
        # 删除向量存储
        vector_store.delete_document_collection(document_id)
        
        # 删除数据库记录
        db.delete(document)
        
        # 删除查询历史
        db.query(QueryHistory).filter(QueryHistory.document_id == document_id).delete()
        
        db.commit()
        
        return {"message": "文档删除成功"}
        
    except Exception as e:
        logger.error(f"文档删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档删除失败: {str(e)}")

@app.get("/api/v1/models/info")
async def get_model_info():
    """获取当前使用的模型信息"""
    return {
        "llm_type": llm_type,
        "embedding_type": embedding_type,
        "available_models": available_models,
        "current_config": {
            "llm_model": os.getenv("QWEN_MODEL", "qwen-plus") if llm_type == "qwen" else os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            "embedding_model": os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v1") if embedding_type == "qwen" else "text-embedding-ada-002"
        }
    }

# 添加处理状态查询接口
@app.get("/api/v1/processing/status")
async def get_processing_status():
    """获取当前处理状态"""
    return {
        "processing_count": len(doc_processor.processing),
        "processing_documents": list(doc_processor.processing),
        "poll_interval": doc_processor.poll_interval,
        "is_running": doc_processor.is_running
    }

# 添加新的重复检测接口
@app.post("/api/v1/documents/check-duplicate")
async def check_duplicate_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """检查文档是否已存在（基于MD5）"""
    
    try:
        # 读取文件内容计算MD5
        file_content = await file.read()
        file_md5 = calculate_content_md5(file_content)
        
        # 检查是否存在重复
        existing_doc_id = is_duplicate_file(db, file_md5)
        
        if existing_doc_id:
            existing_doc = db.query(Document).filter(Document.id == existing_doc_id).first()
            return DuplicateCheckResponse(
                is_duplicate=True,
                existing_document_id=existing_doc_id,
                message=f"文件已存在，文档ID: {existing_doc_id}，状态: {existing_doc.status}"
            )
        else:
            return DuplicateCheckResponse(
                is_duplicate=False,
                existing_document_id=None,
                message="文件未重复，可以上传"
            )
            
    except Exception as e:
        logger.error(f"重复检测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重复检测失败: {str(e)}")

# 添加重试统计接口
@app.get("/api/v1/processing/retry-stats")
async def get_retry_stats(db: Session = Depends(get_db)):
    """获取重试统计信息"""
    
    # 查询各状态的文档数量
    pending_count = db.query(Document).filter(Document.status == "pending").count()
    processing_count = db.query(Document).filter(Document.status == "processing").count()
    completed_count = db.query(Document).filter(Document.status == "completed").count()
    failed_count = db.query(Document).filter(Document.status == "failed").count()
    failed_permanently_count = db.query(Document).filter(Document.status == "failed_permanently").count()
    
    # 查询重试相关统计
    retry_pending = db.query(Document).filter(
        Document.status == "failed",
        Document.retry_count < Document.max_retries
    ).count()
    
    return {
        "document_counts": {
            "pending": pending_count,
            "processing": processing_count,
            "completed": completed_count,
            "failed": failed_count,
            "failed_permanently": failed_permanently_count
        },
        "retry_info": {
            "retry_pending": retry_pending,
            "processing_documents": list(doc_processor.processing),
            "max_retries_default": 3,
            "retry_interval_seconds": doc_processor.retry_interval
        }
    }

@app.get("/api/v1/database/info")
async def get_database_info():
    """获取数据库配置信息"""
    from .database import get_db_info
    
    return {
        "database_info": get_db_info(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug_mode": os.getenv("DEBUG", "false").lower() == "true"
    }

@app.post("/api/v1/documents/{document_id}/enhanced-query")
async def enhanced_query_document(
    document_id: str,
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """增强问答接口 - 使用混合检索和质量评估"""
    
    try:
        # 检查文档是否存在且已完成处理
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")
        
        if document.status != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"文档处理未完成，当前状态: {document.status}"
            )
        
        # 使用增强问答方法
        result = agent.answer_question_enhanced(
            document_id=document_id,
            question=request.question,
            max_results=request.max_results
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "问答处理失败"))
        
        # 保存查询历史
        query_history = QueryHistory(
            document_id=document_id,
            question=request.question,
            answer=result["answer"],
            confidence=result["confidence"],
            processing_time=result["processing_time"]
        )
        db.add(query_history)
        db.commit()
        
        return {
            "answer": result["answer"],
            "confidence": result["confidence"],
            "quality_score": result.get("quality_score", 0.0),
            "sources": result["sources"],
            "processing_time": result["processing_time"],
            "search_method": result.get("search_method", "enhanced"),
            "document_id": document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"增强问答处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail="问答处理失败")

@app.post("/api/v1/documents/{document_id}/enhanced-summary")
async def generate_enhanced_document_summary(document_id: str, db: Session = Depends(get_db)):
    """生成增强文档摘要"""
    
    try:
        # 检查文档状态
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")
        
        if document.status != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"文档处理未完成，当前状态: {document.status}"
            )
        
        # 生成增强摘要
        result = agent.generate_summary_enhanced(document_id)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "摘要生成失败"))
        
        return {
            "document_id": document_id,
            "summary": result["summary"],
            "key_points": result["key_points"],
            "keywords": result["keywords"],
            "quality_score": result["quality_score"],
            "source_chunks": result["source_chunks"],
            "generation_time": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"增强摘要生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail="摘要生成失败")

# 新增文件下载接口
@app.get("/api/v1/documents/{document_id}/download")
async def download_document(document_id: str, db: Session = Depends(get_db)):
    """下载文档文件"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    try:
        # 如果是COS存储，返回预签名URL
        if document.storage_type == "cos":
            file_url = file_storage_manager.get_file_url(
                document_id=document_id,
                storage_type=document.storage_type,
                file_path=document.file_path,
                cos_object_key=document.cos_object_key
            )
            
            if file_url:
                return {
                    "download_url": file_url,
                    "filename": document.filename,
                    "expires_in": 3600,  # 1小时有效期
                    "storage_type": "cos"
                }
            else:
                raise HTTPException(status_code=500, detail="生成下载链接失败")
        
        # 本地存储暂不支持直接下载
        else:
            raise HTTPException(status_code=501, detail="本地存储暂不支持下载功能")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档下载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档下载失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 