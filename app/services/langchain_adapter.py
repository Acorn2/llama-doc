import logging
from typing import List, Dict, Any, Optional

from langchain_community.vectorstores import Qdrant
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document as LCDocument
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.chains import ConversationalRetrievalChain, RetrievalQA
from langchain.memory import ConversationBufferMemory
from langchain.agents import Tool, AgentExecutor, initialize_agent, AgentType
from langchain_core.prompts import PromptTemplate

from app.core.model_factory import ModelFactory
from app.core.qdrant_adapter import QdrantAdapter
from app.services.knowledge_base_service import KnowledgeBaseManager

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
        self.qdrant_client = QdrantAdapter()
        
        # 缓存已创建的检索器
        self.retrievers = {}
        self.conversation_chains = {}
        
    def create_langchain_retriever(self, kb_id: str) -> Any:
        """
        创建LangChain检索器
        
        Args:
            kb_id: 知识库ID
            
        Returns:
            Any: LangChain检索器对象
        """
        if kb_id in self.retrievers:
            return self.retrievers[kb_id]
        
        # 获取知识库的向量存储名称
        vector_store_name = f"kb_{kb_id}"
        
        # 创建Qdrant向量存储
        qdrant_vector_store = Qdrant(
            client=self.qdrant_client.client,
            collection_name=vector_store_name,
            embeddings=self.embeddings
        )
        
        # 创建检索器
        retriever = qdrant_vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        
        # 缓存检索器
        self.retrievers[kb_id] = retriever
        
        logger.info(f"为知识库 {kb_id} 创建LangChain检索器")
        return retriever
    
    def create_conversation_chain(
        self, 
        kb_id: str, 
        conversation_memory=None
    ) -> ConversationalRetrievalChain:
        """
        创建对话链
        
        Args:
            kb_id: 知识库ID
            conversation_memory: 对话内存，可选
            
        Returns:
            ConversationalRetrievalChain: 对话检索链
        """
        # 创建检索器
        retriever = self.create_langchain_retriever(kb_id)
        
        # 创建对话内存
        memory = conversation_memory or ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # 创建中文提示模板
        condense_question_prompt = PromptTemplate.from_template("""
根据以下对话历史和最新问题，生成一个独立、明确的搜索查询。
该查询应该包含所有相关上下文，以便能够在知识库中找到最佳的匹配结果。

对话历史:
{chat_history}

最新问题: {question}

搜索查询:
""")
        
        qa_prompt = PromptTemplate.from_template("""
你是一个专业的智能助手，请基于以下知识库内容回答用户的问题。

知识库内容:
{context}

对话历史:
{chat_history}

用户问题: {question}

回答要求：
1. 严格基于提供的知识库内容回答问题，如果知识库中没有相关信息，请明确说明无法回答
2. 回答要简洁、准确、全面
3. 如果引用了知识库中的内容，可以指明出处
4. 保持客观、中立的语气

回答:
""")
        
        # 创建对话链
        chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            memory=memory,
            condense_question_prompt=condense_question_prompt,
            combine_docs_chain_kwargs={"prompt": qa_prompt},
            return_source_documents=True
        )
        
        logger.info(f"为知识库 {kb_id} 创建对话链")
        return chain
    
    def generate_conversation_response(
        self, 
        kb_id: str, 
        conversation_id: str, 
        user_message: str,
        context: List[Dict[str, Any]] = None,
        search_results: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成对话回复
        
        Args:
            kb_id: 知识库ID
            conversation_id: 对话ID
            user_message: 用户消息
            context: 对话上下文，可选
            search_results: 搜索结果，可选
            
        Returns:
            Dict[str, Any]: 包含回复和元数据的字典
        """
        # 准备对话内存
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # 如果有上下文，添加到内存
        if context:
            for msg in context:
                if msg["role"] == "user":
                    memory.chat_memory.add_user_message(msg["content"])
                elif msg["role"] == "assistant":
                    memory.chat_memory.add_ai_message(msg["content"])
                elif msg["role"] == "system":
                    memory.chat_memory.add_message(SystemMessage(content=msg["content"]))
        
        # 创建对话链
        chain_key = f"{kb_id}:{conversation_id}"
        if chain_key in self.conversation_chains:
            chain = self.conversation_chains[chain_key]
        else:
            chain = self.create_conversation_chain(kb_id, memory)
            self.conversation_chains[chain_key] = chain
        
        # 生成回复
        response = chain({"question": user_message})
        
        # 提取结果
        answer = response["answer"]
        source_documents = response.get("source_documents", [])
        
        # 格式化源文档
        sources = []
        for doc in source_documents:
            sources.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        return {
            "answer": answer,
            "sources": sources
        }
    
    def create_agent(
        self, 
        kb_id: str, 
        conversation_id: Optional[str] = None
    ) -> AgentExecutor:
        """
        创建Agent
        
        Args:
            kb_id: 知识库ID
            conversation_id: 对话ID，可选
            
        Returns:
            AgentExecutor: Agent执行器
        """
        # 创建检索器
        retriever = self.create_langchain_retriever(kb_id)
        
        # 创建基本检索QA链
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever
        )
        
        # 创建工具
        tools = [
            Tool(
                name="KnowledgeBase",
                func=qa_chain.run,
                description="用于在知识库中搜索信息的工具。当你需要回答有关知识库内容的问题时使用此工具。"
            )
        ]
        
        # 使用initialize_agent创建Agent（更兼容的方式）
        agent_executor = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )
        
        logger.info(f"为知识库 {kb_id} 创建Agent")
        return agent_executor
    
    def generate_agent_response(
        self, 
        kb_id: str, 
        user_message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用Agent生成回复
        
        Args:
            kb_id: 知识库ID
            user_message: 用户消息
            conversation_id: 对话ID，可选
            
        Returns:
            Dict[str, Any]: 包含回复和元数据的字典
        """
        # 创建Agent
        agent_executor = self.create_agent(kb_id, conversation_id)
        
        # 执行Agent
        response = agent_executor.run(user_message)
        
        return {
            "answer": response,
            "agent_used": True
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