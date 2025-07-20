"""
基于LangChain的智能Agent核心模块
专注于文档分析和知识问答的Agent实现
"""

import logging
import time
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from langchain_core.tools import BaseTool
from langchain.agents import AgentExecutor, initialize_agent, AgentType
from langchain.tools import Tool
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory

from app.core.model_factory import ModelFactory
from app.services.langchain_adapter import LangChainAdapter

logger = logging.getLogger(__name__)

class DocumentAnalysisTool(BaseTool):
    """文档分析工具"""
    
    name: str = "document_analyzer"
    description: str = "分析文档内容，提取关键信息、总结要点或回答特定问题"
    
    def __init__(self, langchain_adapter: LangChainAdapter, kb_id: str):
        super().__init__()
        self.adapter = langchain_adapter
        self.kb_id = kb_id
    
    def _run(self, query: str) -> str:
        """执行文档分析"""
        try:
            # 使用检索器获取相关文档
            retriever = self.adapter.create_langchain_retriever(self.kb_id)
            docs = retriever.get_relevant_documents(query)
            
            if not docs:
                return "未找到相关文档内容"
            
            # 构建上下文
            context = "\n\n".join([doc.page_content for doc in docs[:3]])
            
            # 使用LLM分析
            prompt = ChatPromptTemplate.from_template("""
基于以下文档内容，请回答用户的问题或完成分析任务：

文档内容：
{context}

用户请求：{query}

请提供准确、详细的分析结果：
""")
            
            chain = prompt | self.adapter.llm | StrOutputParser()
            result = chain.invoke({"context": context, "query": query})
            
            return result
            
        except Exception as e:
            logger.error(f"文档分析工具执行失败: {e}")
            return f"分析失败: {str(e)}"

class KnowledgeSearchTool(BaseTool):
    """知识库搜索工具"""
    
    name: str = "knowledge_search"
    description: str = "在知识库中搜索特定信息，支持语义搜索和关键词搜索"
    
    def __init__(self, langchain_adapter: LangChainAdapter, kb_id: str):
        super().__init__()
        self.adapter = langchain_adapter
        self.kb_id = kb_id
    
    def _run(self, query: str) -> str:
        """执行知识搜索"""
        try:
            retriever = self.adapter.create_langchain_retriever(self.kb_id)
            docs = retriever.get_relevant_documents(query)
            
            if not docs:
                return "未找到相关信息"
            
            # 格式化搜索结果
            results = []
            for i, doc in enumerate(docs[:5], 1):
                results.append(f"结果 {i}:\n{doc.page_content[:300]}...")
            
            return "\n\n".join(results)
            
        except Exception as e:
            logger.error(f"知识搜索工具执行失败: {e}")
            return f"搜索失败: {str(e)}"

class SummaryTool(BaseTool):
    """文档摘要工具"""
    
    name: str = "document_summary"
    description: str = "生成文档摘要，提取核心观点和关键信息"
    
    def __init__(self, langchain_adapter: LangChainAdapter, kb_id: str):
        super().__init__()
        self.adapter = langchain_adapter
        self.kb_id = kb_id
    
    def _run(self, query: str = "生成文档摘要") -> str:
        """生成文档摘要"""
        try:
            retriever = self.adapter.create_langchain_retriever(self.kb_id)
            docs = retriever.get_relevant_documents("文档主要内容 核心观点 关键信息")
            
            if not docs:
                return "无法生成摘要：未找到文档内容"
            
            # 构建摘要内容
            content = "\n\n".join([doc.page_content for doc in docs[:8]])
            
            prompt = ChatPromptTemplate.from_template("""
请为以下文档内容生成一份高质量的中文摘要：

文档内容：
{content}

摘要要求：
1. 准确概括文档的核心观点、主要发现和重要结论
2. 突出文档的学术价值和创新点
3. 保持逻辑结构清晰，语言表达准确
4. 摘要长度控制在300-600字之间
5. 使用规范的学术写作风格

摘要：
""")
            
            chain = prompt | self.adapter.llm | StrOutputParser()
            summary = chain.invoke({"content": content})
            
            return summary
            
        except Exception as e:
            logger.error(f"摘要工具执行失败: {e}")
            return f"摘要生成失败: {str(e)}"

class LangChainDocumentAgent:
    """基于LangChain的文档分析Agent"""
    
    def __init__(
        self,
        kb_id: str,
        llm_type: str = "qwen",
        model_config: Optional[Dict] = None,
        enable_memory: bool = True
    ):
        """
        初始化文档分析Agent
        
        Args:
            kb_id: 知识库ID
            llm_type: LLM类型
            model_config: 模型配置
            enable_memory: 是否启用对话记忆
        """
        self.kb_id = kb_id
        self.enable_memory = enable_memory
        
        # 初始化LangChain适配器
        self.adapter = LangChainAdapter(
            llm=ModelFactory.create_llm(llm_type, **(model_config or {})),
            embeddings=ModelFactory.create_embeddings()
        )
        
        # 初始化工具
        self.tools = self._create_tools()
        
        # 初始化Agent
        self.agent_executor = self._create_agent()
        
        # 对话记忆
        if enable_memory:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        else:
            self.memory = None
        
        logger.info(f"LangChain文档Agent初始化完成 - KB: {kb_id}")
    
    def _create_tools(self) -> List[BaseTool]:
        """创建Agent工具"""
        tools = [
            DocumentAnalysisTool(self.adapter, self.kb_id),
            KnowledgeSearchTool(self.adapter, self.kb_id),
            SummaryTool(self.adapter, self.kb_id)
        ]
        
        return tools
    
    def _create_agent(self) -> AgentExecutor:
        """创建Agent执行器"""
        # 使用initialize_agent创建Agent（更兼容的方式）
        agent_executor = initialize_agent(
            tools=self.tools,
            llm=self.adapter.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
        
        return agent_executor
    
    def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        use_agent: bool = True
    ) -> Dict[str, Any]:
        """
        与Agent对话 - 增强错误处理，确保返回格式正确
        
        Args:
            message: 用户消息
            conversation_id: 对话ID
            use_agent: 是否使用Agent模式
            
        Returns:
            Dict[str, Any]: 包含回复和元数据的响应
        """
        start_time = time.time()
        current_timestamp = datetime.now().isoformat()
        
        try:
            if use_agent:
                # 使用Agent模式 - 但避免使用可能有问题的agent_executor
                try:
                    response = self.adapter.generate_agent_response(
                        kb_id=self.kb_id,
                        user_message=message,
                        conversation_id=conversation_id
                    )
                    answer = response.get("answer", "抱歉，我无法处理您的请求。")
                    tools_used = ["agent_chain"] if response.get("agent_used", False) else []
                except Exception as agent_error:
                    logger.warning(f"Agent模式失败，回退到对话模式: {agent_error}")
                    # 回退到对话模式
                    response = self.adapter.generate_conversation_response(
                        kb_id=self.kb_id,
                        conversation_id=conversation_id or "default",
                        user_message=message
                    )
                    answer = response.get("answer", "抱歉，我无法处理您的请求。")
                    tools_used = []
            else:
                # 使用简单对话模式
                response = self.adapter.generate_conversation_response(
                    kb_id=self.kb_id,
                    conversation_id=conversation_id or "default",
                    user_message=message
                )
                answer = response.get("answer", "抱歉，我无法处理您的请求。")
                tools_used = []
            
            # 确保answer不为空
            if not answer or answer.strip() == "":
                answer = "抱歉，我无法生成有效的回复，请稍后重试。"
            
            # 更新记忆
            if self.memory:
                try:
                    self.memory.chat_memory.add_user_message(message)
                    self.memory.chat_memory.add_ai_message(answer)
                except Exception as memory_error:
                    logger.warning(f"更新记忆失败: {memory_error}")
            
            processing_time = time.time() - start_time
            
            return {
                "answer": answer,
                "tools_used": tools_used,
                "processing_time": processing_time,
                "agent_mode": use_agent,
                "conversation_id": conversation_id or "default",
                "timestamp": current_timestamp,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Agent对话失败: {e}")
            processing_time = time.time() - start_time
            
            # 确保即使在异常情况下也返回正确格式的响应
            return {
                "answer": "抱歉，处理您的请求时发生了错误，请稍后重试。",
                "tools_used": [],
                "processing_time": processing_time,
                "agent_mode": use_agent,
                "conversation_id": conversation_id or "default",
                "timestamp": current_timestamp,
                "success": False,
                "error": str(e)
            }
    
    def analyze_document(self, query: str) -> Dict[str, Any]:
        """
        分析文档
        
        Args:
            query: 分析查询
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        start_time = time.time()
        
        try:
            # 使用文档分析工具
            analysis_tool = DocumentAnalysisTool(self.adapter, self.kb_id)
            result = analysis_tool._run(query)
            
            return {
                "analysis": result,
                "query": query,
                "processing_time": time.time() - start_time,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            return {
                "analysis": "文档分析失败",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "success": False
            }
    
    def generate_summary(self) -> Dict[str, Any]:
        """
        生成文档摘要
        
        Returns:
            Dict[str, Any]: 摘要结果
        """
        start_time = time.time()
        
        try:
            # 使用摘要工具
            summary_tool = SummaryTool(self.adapter, self.kb_id)
            summary = summary_tool._run()
            
            return {
                "summary": summary,
                "processing_time": time.time() - start_time,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            return {
                "summary": "摘要生成失败",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "success": False
            }
    
    def search_knowledge(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        搜索知识库
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        start_time = time.time()
        
        try:
            # 使用知识搜索工具
            search_tool = KnowledgeSearchTool(self.adapter, self.kb_id)
            results = search_tool._run(query)
            
            return {
                "results": results,
                "query": query,
                "processing_time": time.time() - start_time,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"知识搜索失败: {e}")
            return {
                "results": "搜索失败",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "success": False
            }
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        if not self.memory:
            return []
        
        history = []
        for message in self.memory.chat_memory.messages:
            if isinstance(message, HumanMessage):
                history.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "assistant", "content": message.content})
            elif isinstance(message, SystemMessage):
                history.append({"role": "system", "content": message.content})
        
        return history
    
    def clear_memory(self):
        """清除对话记忆"""
        if self.memory:
            self.memory.clear()
            logger.info("Agent对话记忆已清除")
    
    def add_custom_tool(self, tool: BaseTool):
        """添加自定义工具"""
        self.tools.append(tool)
        # 重新创建Agent
        self.agent_executor = self._create_agent()
        logger.info(f"添加自定义工具: {tool.name}")