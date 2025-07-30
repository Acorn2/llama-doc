"""
流式输出工具类
实现打字机效果的流式数据输出
"""

import asyncio
import json
import time
import re
from typing import AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class StreamChunkType(Enum):
    """流式数据块类型"""
    CONTENT = "content"          # 内容块
    METADATA = "metadata"        # 元数据块
    ERROR = "error"              # 错误块
    FINAL = "final"              # 最终块
    HEARTBEAT = "heartbeat"      # 心跳块


@dataclass
class StreamChunk:
    """流式数据块"""
    type: StreamChunkType
    content: str = ""
    metadata: Optional[Dict[str, Any]] = None
    is_final: bool = False
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata or {},
            "is_final": self.is_final,
            "timestamp": self.timestamp
        }
    
    def to_sse_format(self) -> str:
        """转换为SSE格式"""
        data = json.dumps(self.to_dict(), ensure_ascii=False)
        return f"data: {data}\n\n"


class TypewriterStreamer:
    """打字机效果流式输出器"""
    
    def __init__(
        self,
        chunk_size: int = 1,                    # 固定字符数（当enable_random=False时）
        chunk_size_range: tuple = (1, 3),       # 随机字符数范围
        delay: float = 0.05,                    # 固定延迟（当enable_random=False时）
        delay_range: tuple = (0.03, 0.08),      # 随机延迟范围
        sentence_delay: float = 0.2,            # 句子结束后的延迟
        paragraph_delay: float = 0.5,           # 段落结束后的延迟
        word_delay: float = 0.1,                # 单词结束后的延迟
        enable_smart_delay: bool = True,        # 是否启用智能延迟
        enable_random: bool = True              # 是否启用随机效果
    ):
        self.chunk_size = chunk_size
        self.chunk_size_range = chunk_size_range
        self.delay = delay
        self.delay_range = delay_range
        self.sentence_delay = sentence_delay
        self.paragraph_delay = paragraph_delay
        self.word_delay = word_delay
        self.enable_smart_delay = enable_smart_delay
        self.enable_random = enable_random
        
        # 句子结束标点符号
        self.sentence_endings = {'。', '！', '？', '.', '!', '?', '；', ';'}
        # 段落结束标记
        self.paragraph_endings = {'\n\n', '\n'}
        # 单词分隔符
        self.word_separators = {' ', '\t', '，', ',', '、'}
    
    async def stream_text(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        流式输出文本，实现打字机效果
        
        Args:
            text: 要输出的文本
            metadata: 附加元数据
            
        Yields:
            StreamChunk: 流式数据块
        """
        if not text:
            yield StreamChunk(
                type=StreamChunkType.FINAL,
                content="",
                metadata=metadata,
                is_final=True
            )
            return
        
        # 发送开始元数据
        if metadata:
            yield StreamChunk(
                type=StreamChunkType.METADATA,
                metadata=metadata
            )
        
        # 按字符或块大小分割文本
        chunks = self._split_text(text)
        
        for i, chunk in enumerate(chunks):
            # 发送内容块
            yield StreamChunk(
                type=StreamChunkType.CONTENT,
                content=chunk,
                is_final=False
            )
            
            # 计算延迟时间
            delay_time = self._calculate_delay(chunk, i < len(chunks) - 1)
            
            # 异步延迟
            if delay_time > 0:
                await asyncio.sleep(delay_time)
        
        # 发送最终块
        yield StreamChunk(
            type=StreamChunkType.FINAL,
            content="",
            metadata={"total_length": len(text)},
            is_final=True
        )
    
    def _split_text(self, text: str) -> List[str]:
        """随机分割文本为合适的块"""
        if not self.enable_random:
            # 固定模式
            if self.chunk_size == 1:
                return list(text)
            chunks = []
            for i in range(0, len(text), self.chunk_size):
                chunks.append(text[i:i + self.chunk_size])
            return chunks
        
        # 随机模式
        import random
        chunks = []
        i = 0
        while i < len(text):
            # 随机选择chunk大小
            chunk_size = random.randint(*self.chunk_size_range)
            chunk = text[i:i + chunk_size]
            chunks.append(chunk)
            i += chunk_size
        
        return chunks
    
    def _calculate_delay(self, chunk: str, has_next: bool) -> float:
        """计算延迟时间（支持随机延迟）"""
        import random
        
        # 基础延迟
        if self.enable_random:
            base_delay = random.uniform(*self.delay_range)
        else:
            base_delay = self.delay
        
        if not self.enable_smart_delay:
            return base_delay
        
        # 智能延迟逻辑
        if any(ending in chunk for ending in self.sentence_endings):
            return self.sentence_delay if has_next else base_delay
        
        if any(ending in chunk for ending in self.paragraph_endings):
            return self.paragraph_delay if has_next else base_delay
        
        if any(sep in chunk for sep in self.word_separators):
            return self.word_delay if has_next else base_delay
        
        return base_delay


class ConversationStreamer:
    """对话流式输出器"""
    
    def __init__(self, typewriter: Optional[TypewriterStreamer] = None):
        self.typewriter = typewriter or TypewriterStreamer()
    
    async def stream_conversation_response(
        self,
        response_text: str,
        conversation_id: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        processing_time: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式输出对话响应
        
        Args:
            response_text: 响应文本
            conversation_id: 对话ID
            sources: 引用来源
            processing_time: 处理时间
            
        Yields:
            str: SSE格式的数据
        """
        metadata = {
            "conversation_id": conversation_id,
            "sources": sources or [],
            "processing_time": processing_time
        }
        
        async for chunk in self.typewriter.stream_text(response_text, metadata):
            yield chunk.to_sse_format()


class AgentStreamer:
    """Agent流式输出器"""
    
    def __init__(self, typewriter: Optional[TypewriterStreamer] = None):
        self.typewriter = typewriter or TypewriterStreamer()
    
    async def stream_agent_response(
        self,
        response_data: Dict[str, Any],
        kb_id: str,
        use_agent: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        流式输出Agent响应
        
        Args:
            response_data: Agent响应数据
            kb_id: 知识库ID
            use_agent: 是否使用Agent模式
            
        Yields:
            str: SSE格式的数据
        """
        # 提取响应文本
        response_text = ""
        if isinstance(response_data, dict):
            response_text = response_data.get("answer", "") or response_data.get("content", "")
        elif isinstance(response_data, str):
            response_text = response_data
        
        metadata = {
            "kb_id": kb_id,
            "use_agent": use_agent,
            "agent_mode": response_data.get("agent_mode", "unknown") if isinstance(response_data, dict) else "text",
            "processing_time": response_data.get("processing_time") if isinstance(response_data, dict) else None
        }
        
        async for chunk in self.typewriter.stream_text(response_text, metadata):
            yield chunk.to_sse_format()


class RealTimeStreamer:
    """真正的实时流式处理器"""
    
    def __init__(self, typewriter: Optional[TypewriterStreamer] = None):
        self.typewriter = typewriter or TypewriterStreamer()
    
    async def process_llm_stream(
        self,
        llm_stream_generator,
        conversation_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        处理LLM的流式输出，实时应用打字机效果
        
        Args:
            llm_stream_generator: LLM流式生成器
            conversation_id: 对话ID
            metadata: 元数据
            
        Yields:
            str: SSE格式的数据
        """
        accumulated_text = ""
        
        # 发送开始元数据
        if metadata:
            start_chunk = StreamChunk(
                type=StreamChunkType.METADATA,
                metadata={**metadata, "conversation_id": conversation_id}
            )
            yield start_chunk.to_sse_format()
        
        try:
            # 处理LLM流式输出
            for chunk_data in llm_stream_generator:
                if chunk_data.get("is_final"):
                    # 处理最终块
                    final_metadata = {
                        "conversation_id": conversation_id,
                        "total_length": len(accumulated_text),
                        "sources": chunk_data.get("sources", []),
                        "processing_time": chunk_data.get("processing_time", 0)
                    }
                    
                    final_chunk = StreamChunk(
                        type=StreamChunkType.FINAL,
                        content="",
                        metadata=final_metadata,
                        is_final=True
                    )
                    yield final_chunk.to_sse_format()
                    break
                else:
                    # 实时处理每个chunk
                    chunk_text = chunk_data.get("chunk", "")
                    if chunk_text:
                        accumulated_text += chunk_text
                        
                        # 使用打字机效果处理这个chunk
                        async for typewriter_chunk in self.typewriter.stream_text(chunk_text):
                            if typewriter_chunk.type == StreamChunkType.CONTENT:
                                content_chunk = StreamChunk(
                                    type=StreamChunkType.CONTENT,
                                    content=typewriter_chunk.content,
                                    metadata={"conversation_id": conversation_id},
                                    is_final=False
                                )
                                yield content_chunk.to_sse_format()
                                
        except Exception as e:
            # 发送错误信息
            error_chunk = StreamChunk(
                type=StreamChunkType.ERROR,
                content=f"流式处理错误: {str(e)}",
                metadata={"conversation_id": conversation_id},
                is_final=True
            )
            yield error_chunk.to_sse_format()


class StreamingResponseBuilder:
    """流式响应构建器"""
    
    @staticmethod
    def create_conversation_stream(
        response_text: str,
        conversation_id: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        processing_time: Optional[float] = None,
        typewriter_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        创建对话流式响应（用于完整文本的打字机效果）
        
        Args:
            response_text: 响应文本
            conversation_id: 对话ID
            sources: 引用来源
            processing_time: 处理时间
            typewriter_config: 打字机配置
            
        Returns:
            AsyncGenerator[str, None]: 流式数据生成器
        """
        config = typewriter_config or {}
        typewriter = TypewriterStreamer(**config)
        streamer = ConversationStreamer(typewriter)
        
        return streamer.stream_conversation_response(
            response_text, conversation_id, sources, processing_time
        )
    
    @staticmethod
    def create_realtime_stream(
        llm_stream_generator,
        conversation_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        typewriter_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        创建真正的实时流式响应
        
        Args:
            llm_stream_generator: LLM流式生成器
            conversation_id: 对话ID
            metadata: 元数据
            typewriter_config: 打字机配置
            
        Returns:
            AsyncGenerator[str, None]: 流式数据生成器
        """
        config = typewriter_config or {}
        typewriter = TypewriterStreamer(**config)
        streamer = RealTimeStreamer(typewriter)
        
        return streamer.process_llm_stream(
            llm_stream_generator, conversation_id, metadata
        )
    
    @staticmethod
    def create_agent_stream(
        response_data: Dict[str, Any],
        kb_id: str,
        use_agent: bool = True,
        typewriter_config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        创建Agent流式响应
        
        Args:
            response_data: Agent响应数据
            kb_id: 知识库ID
            use_agent: 是否使用Agent模式
            typewriter_config: 打字机配置
            
        Returns:
            AsyncGenerator[str, None]: 流式数据生成器
        """
        config = typewriter_config or {}
        typewriter = TypewriterStreamer(**config)
        streamer = AgentStreamer(typewriter)
        
        return streamer.stream_agent_response(response_data, kb_id, use_agent)


# 预设配置
class StreamingPresets:
    """流式输出预设配置"""
    
    # 快速模式 - 适合演示
    FAST = {
        "chunk_size_range": (2, 4),
        "delay_range": (0.01, 0.03),
        "sentence_delay": 0.1,
        "paragraph_delay": 0.2,
        "word_delay": 0.05,
        "enable_smart_delay": True,
        "enable_random": True
    }
    
    # 标准模式 - 平衡体验
    STANDARD = {
        "chunk_size_range": (1, 3),
        "delay_range": (0.03, 0.06),
        "sentence_delay": 0.2,
        "paragraph_delay": 0.5,
        "word_delay": 0.1,
        "enable_smart_delay": True,
        "enable_random": True
    }
    
    # 慢速模式 - 更真实的打字效果
    SLOW = {
        "chunk_size_range": (1, 2),
        "delay_range": (0.08, 0.15),
        "sentence_delay": 0.5,
        "paragraph_delay": 1.0,
        "word_delay": 0.2,
        "enable_smart_delay": True,
        "enable_random": True
    }
    
    # 无延迟模式 - 快速输出
    NO_DELAY = {
        "chunk_size": 10,
        "delay": 0.0,
        "sentence_delay": 0.0,
        "paragraph_delay": 0.0,
        "word_delay": 0.0,
        "enable_smart_delay": False,
        "enable_random": False
    }
    
    # 自然打字效果 - 最接近真实打字
    NATURAL = {
        "chunk_size_range": (1, 3),
        "delay_range": (0.02, 0.06),
        "sentence_delay": 0.15,
        "paragraph_delay": 0.3,
        "word_delay": 0.08,
        "enable_smart_delay": True,
        "enable_random": True
    }
    
    # 快速自然效果
    FAST_NATURAL = {
        "chunk_size_range": (2, 4),
        "delay_range": (0.01, 0.03),
        "sentence_delay": 0.1,
        "paragraph_delay": 0.2,
        "word_delay": 0.05,
        "enable_smart_delay": True,
        "enable_random": True
    }


# 便捷函数
async def create_typewriter_stream(
    text: str,
    preset: str = "STANDARD",
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    创建打字机效果的流式输出
    
    Args:
        text: 要输出的文本
        preset: 预设配置名称 (FAST, STANDARD, SLOW, NO_DELAY)
        **kwargs: 额外的配置参数
        
    Yields:
        str: SSE格式的数据
    """
    config = getattr(StreamingPresets, preset.upper(), StreamingPresets.STANDARD)
    config.update(kwargs)
    
    typewriter = TypewriterStreamer(**config)
    
    async for chunk in typewriter.stream_text(text):
        yield chunk.to_sse_format()