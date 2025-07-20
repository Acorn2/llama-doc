import logging
from typing import List, Dict, Any, Optional

from langchain_community.vectorstores import Qdrant
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document as LCDocument
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.agents import Tool, AgentExecutor, initialize_agent, AgentType
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.core.model_factory import ModelFactory
from app.core.qdrant_adapter import QdrantAdapter
from app.services.knowledge_base_service import KnowledgeBaseManager
import os

logger = logging.getLogger(__name__)

class LangChainAdapter:
    """LangChain集成模块"""
    
    def __init__(
        self, 
        vector_store_manager=None, 
        kb_manager=None,
        llm=None, 
        embeddings=None
    ):
        """
        初始化LangChain适配器
        
        Args:
            vector_store_manager: 向量存储管理器
            kb_manager: 知识库管理器
            llm: 大语言模型
            embeddings: 嵌入模型
        """
        self.kb_manager = kb_manager or KnowledgeBaseManager()
        self.llm = llm or ModelFactory.create_llm()
        self.embeddings = embeddings or ModelFactory.create_embeddings()
        
        # 使用正确的环境变量配置创建QdrantAdapter
        self.qdrant_client = QdrantAdapter(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            use_https=os.getenv("QDRANT_HTTPS", "false").lower() == "true",
            api_key=os.getenv("QDRANT_API_KEY")
        )
        
        # 缓存已创建的检索器
        self.retrievers = {}
        self.conversation_chains = {}
        
    def create_langchain_retriever(self, kb_id: str) -> Any:
        """
        创建LangChain检索器 - 增强错误处理和空内容过滤
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            Any: 自定义检索器对象
            
        Raises:
            Exception: 当无法创建检索器时抛出异常
        """
        if kb_id in self.retrievers:
            return self.retrievers[kb_id]
        
        try:
            # 获取知识库的向量存储名称
            vector_store_name = f"kb_{kb_id}"
            
            # 创建自定义检索器类来处理空内容问题
            class SafeRetriever:
                def __init__(self, qdrant_client, collection_name, embeddings):
                    self.qdrant_client = qdrant_client
                    self.collection_name = collection_name
                    self.embeddings = embeddings
                
                def __or__(self, other):
                    """支持管道操作符 | 用于LCEL链"""
                    from langchain_core.runnables import RunnableLambda
                    
                    def combined_func(query):
                        docs = self.get_relevant_documents(query)
                        return other(docs)
                    
                    return RunnableLambda(combined_func)
                
                def get_relevant_documents(self, query: str) -> List[LCDocument]:
                    """安全的文档检索，过滤空内容"""
                    try:
                        # 生成查询向量
                        query_embedding = self.embeddings.embed_query(query)
                        
                        # 直接使用 Qdrant 客户端搜索
                        search_results = self.qdrant_client.search(
                            collection_name=self.collection_name,
                            query_vector=query_embedding,
                            limit=5,
                            with_payload=True
                        )
                        
                        # 创建 LangChain Document 对象，过滤空内容
                        documents = []
                        for result in search_results:
                            payload = result.get('payload', {})
                            content = payload.get('content', '')
                            
                            # 确保内容不为空
                            if content and content.strip():
                                doc = LCDocument(
                                    page_content=content.strip(),
                                    metadata={
                                        'chunk_id': payload.get('chunk_id', ''),
                                        'document_id': payload.get('document_id', ''),
                                        'chunk_index': payload.get('chunk_index', 0),
                                        'similarity_score': result.get('score', 0.0),
                                        'keywords': payload.get('keywords', []),
                                        'summary': payload.get('summary', ''),
                                        'quality_score': payload.get('quality_score', 0.5)
                                    }
                                )
                                documents.append(doc)
                        
                        logger.info(f"安全检索完成，返回 {len(documents)} 个有效文档")
                        return documents
                        
                    except Exception as e:
                        logger.error(f"安全检索失败: {e}")
                        return []
            
            # 创建自定义检索器
            retriever = SafeRetriever(
                qdrant_client=self.qdrant_client,
                collection_name=vector_store_name,
                embeddings=self.embeddings
            )
            
            # 缓存检索器
            self.retrievers[kb_id] = retriever
            
            logger.info(f"为知识库 {kb_id} 创建安全检索器")
            return retriever
            
        except Exception as e:
            logger.error(f"创建LangChain检索器失败: {e}")
            # 检查是否是Qdrant连接问题
            if "502" in str(e) or "Bad Gateway" in str(e) or "Connection" in str(e):
                raise Exception(f"向量数据库连接失败: {str(e)}")
            else:
                raise Exception(f"检索器创建失败: {str(e)}")
    
    def create_conversation_chain(
        self, 
        kb_id: str, 
        conversation_memory=None
    ) -> Any:
        """
        创建对话链 - 使用LCEL方式避免LLMChain兼容性问题，增强错误处理
        
        Args:
            kb_id: 知识库ID
            conversation_memory: 对话内存，可选
            
        Returns:
            Any: 对话检索链或回退链
        """
        try:
            # 尝试创建检索器
            retriever = self.create_langchain_retriever(kb_id)
            
            # 创建提示模板
            prompt = ChatPromptTemplate.from_template("""
基于以下文档内容回答用户问题：

文档内容：
{context}

用户问题：{question}

请基于提供的文档内容给出准确、详细的回答。如果文档中没有相关信息，请说明无法从提供的文档中找到答案。
""")
            
            # 定义格式化上下文的函数，过滤空内容
            def format_docs(docs):
                valid_contents = []
                for doc in docs:
                    # 确保 page_content 不为 None 且不为空
                    if doc.page_content and doc.page_content.strip():
                        valid_contents.append(doc.page_content.strip())
                
                if not valid_contents:
                    return "暂无相关文档内容"
                
                return "\n\n".join(valid_contents)
            
            # 使用LCEL创建链
            chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
            )
            
            logger.info(f"为知识库 {kb_id} 创建LCEL链")
            return chain
            
        except Exception as e:
            logger.error(f"创建对话链失败: {e}")
            
            # 创建回退链 - 不依赖检索器的简单对话链
            logger.info(f"为知识库 {kb_id} 创建回退对话链")
            
            fallback_prompt = ChatPromptTemplate.from_template("""
用户问题：{question}

抱歉，当前无法访问知识库内容，但我会尽力基于我的知识来回答您的问题。如果需要查询特定文档内容，请稍后重试。

请回答：
""")
            
            fallback_chain = (
                {"question": RunnablePassthrough()}
                | fallback_prompt
                | self.llm
                | StrOutputParser()
            )
            
            return fallback_chain
    
    def generate_conversation_response(
        self, 
        kb_id: str, 
        conversation_id: str, 
        user_message: str,
        context: List[Dict[str, Any]] = None,
        search_results: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成对话回复 - 适配LCEL链，增强错误处理
        
        Args:
            kb_id: 知识库ID
            conversation_id: 对话ID
            user_message: 用户消息
            context: 对话上下文，可选
            search_results: 搜索结果，可选
            
        Returns:
            Dict[str, Any]: 包含回复和元数据的字典
        """
        try:
            # 先获取源文档
            sources = []
            retrieved_docs = []
            try:
                retriever = self.create_langchain_retriever(kb_id)
                source_documents = retriever.get_relevant_documents(user_message)
                
                # 格式化源文档，过滤空内容
                for doc in source_documents:
                    # 确保 page_content 不为 None 且不为空
                    if doc.page_content and doc.page_content.strip():
                        sources.append({
                            "content": doc.page_content.strip(),
                            "metadata": doc.metadata or {}
                        })
                        retrieved_docs.append(doc)
                
                logger.info(f"获取到 {len(sources)} 个有效源文档")
            except Exception as source_error:
                logger.warning(f"获取源文档失败，但对话继续: {source_error}")
                sources = []
                retrieved_docs = []
            
            # 如果有检索到的文档，直接使用这些文档生成回复
            if retrieved_docs:
                # 创建提示模板
                prompt = ChatPromptTemplate.from_template("""
基于以下文档内容回答用户问题：

文档内容：
{context}

用户问题：{question}

请基于提供的文档内容给出准确、详细的回答。如果文档中没有相关信息，请说明无法从提供的文档中找到答案。
""")
                
                # 格式化文档内容
                context_text = "\n\n".join([doc.page_content.strip() for doc in retrieved_docs])
                
                # 直接使用提示模板生成回复
                formatted_prompt = prompt.format(context=context_text, question=user_message)
                answer = self.llm.invoke(formatted_prompt)
                
                logger.info(f"使用 {len(retrieved_docs)} 个文档生成回复")
            else:
                # 如果没有检索到文档，使用回退链
                fallback_prompt = ChatPromptTemplate.from_template("""
用户问题：{question}

抱歉，当前无法从知识库中找到相关的文档内容来回答您的问题。我会尽力基于我的知识来回答您的问题。

请回答：
""")
                
                formatted_prompt = fallback_prompt.format(question=user_message)
                answer = self.llm.invoke(formatted_prompt)
                
                logger.info("使用回退模式生成回复")
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"生成对话回复失败: {e}")
            # 检查是否是Qdrant连接问题
            if "502" in str(e) or "Bad Gateway" in str(e):
                error_msg = "向量数据库连接异常，请稍后重试。"
            else:
                error_msg = "抱歉，处理您的请求时发生了错误，请稍后重试。"
            
            return {
                "answer": error_msg,
                "sources": []
            }
    
    def create_agent(
        self, 
        kb_id: str, 
        conversation_id: Optional[str] = None
    ) -> Any:
        """
        创建Agent - 完全避免LLMChain，直接返回LCEL链
        
        Args:
            kb_id: 知识库ID
            conversation_id: 对话ID，可选
            
        Returns:
            Any: 简化的Agent（实际上是LCEL链）
        """
        # 直接返回对话链，避免Agent的复杂性和LLMChain问题
        qa_chain = self.create_conversation_chain(kb_id)
        
        logger.info(f"为知识库 {kb_id} 创建简化Agent（LCEL链）")
        return qa_chain
    
    def generate_agent_response(
        self, 
        kb_id: str, 
        user_message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用Agent生成回复 - 直接使用LCEL链
        
        Args:
            kb_id: 知识库ID
            user_message: 用户消息
            conversation_id: 对话ID，可选
            
        Returns:
            Dict[str, Any]: 包含回复和元数据的字典
        """
        try:
            # 创建Agent（实际上是LCEL链）
            agent_chain = self.create_agent(kb_id, conversation_id)
            
            # 直接使用LCEL链处理用户消息
            answer = agent_chain.invoke(user_message)
            
            return {
                "answer": answer,
                "agent_used": True
            }
            
        except Exception as e:
            logger.error(f"Agent生成回复失败: {e}")
            # 如果失败，回退到直接使用对话链
            try:
                chain = self.create_conversation_chain(kb_id)
                answer = chain.invoke(user_message)
                return {
                    "answer": answer,
                    "agent_used": False
                }
            except Exception as fallback_error:
                logger.error(f"回退方案也失败: {fallback_error}")
                return {
                    "answer": "抱歉，处理您的请求时发生了错误，请稍后重试。",
                    "agent_used": False
                }
    
    def clear_cache(self, kb_id: Optional[str] = None, conversation_id: Optional[str] = None):
        """
        清除缓存
        
        Args:
            kb_id: 知识库ID，可选
            conversation_id: 对话ID，可选
        """
        if kb_id and conversation_id:
            # 清除特定对话链
            chain_key = f"{kb_id}:{conversation_id}"
            if chain_key in self.conversation_chains:
                del self.conversation_chains[chain_key]
        elif kb_id:
            # 清除特定知识库的所有缓存
            if kb_id in self.retrievers:
                del self.retrievers[kb_id]
            
            # 清除相关的对话链
            keys_to_delete = []
            for key in self.conversation_chains:
                if key.startswith(f"{kb_id}:"):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.conversation_chains[key]
        else:
            # 清除所有缓存
            self.retrievers = {}
            self.conversation_chains = {}
        
        logger.info(f"清除缓存 - KB: {kb_id}, 对话: {conversation_id}") 