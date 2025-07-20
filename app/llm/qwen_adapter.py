import os
import dashscope
from typing import List, Dict, Any, Optional, Union, Iterator
from langchain_core.language_models.llms import BaseLLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import Generation, LLMResult
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable
from langchain_core.runnables.config import RunnableConfig
from pydantic import Field
import logging

logger = logging.getLogger(__name__)

class QwenLLM(BaseLLM):
    """通义千问大模型适配器 - 完全兼容LangChain Runnable接口"""
    
    model_name: str = Field(default="qwen-plus", description="模型名称")
    temperature: float = Field(default=0.1, description="温度参数")
    max_tokens: int = Field(default=2000, description="最大token数")
    top_p: float = Field(default=0.8, description="top_p参数")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 设置API密钥
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("请设置DASHSCOPE_API_KEY环境变量")
        
        dashscope.api_key = api_key
    
    @property
    def _llm_type(self) -> str:
        return "qwen"
    
    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """生成响应 - LangChain标准接口"""
        generations = []
        
        for prompt in prompts:
            try:
                response = dashscope.Generation.call(
                    model=self.model_name,
                    prompt=prompt,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    stop=stop,
                    **kwargs
                )
                
                if response.status_code == 200:
                    text = response.output.text
                    generation = Generation(text=text)
                    generations.append([generation])
                else:
                    logger.error(f"通义千问API调用失败: {response.message}")
                    raise Exception(f"API调用失败: {response.message}")
                    
            except Exception as e:
                logger.error(f"通义千问调用异常: {str(e)}")
                raise e
        
        return LLMResult(generations=generations)
    
    async def _agenerate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """异步生成响应 - LangChain标准接口"""
        generations = []
        
        for prompt in prompts:
            try:
                response = await dashscope.AGeneration.call(
                    model=self.model_name,
                    prompt=prompt,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    stop=stop,
                    **kwargs
                )
                
                if response.status_code == 200:
                    text = response.output.text
                    generation = Generation(text=text)
                    generations.append([generation])
                else:
                    logger.error(f"通义千问异步API调用失败: {response.message}")
                    raise Exception(f"异步API调用失败: {response.message}")
                    
            except Exception as e:
                logger.error(f"通义千问异步调用异常: {str(e)}")
                raise e
        
        return LLMResult(generations=generations)
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """单个调用 - 兼容旧版本接口"""
        result = self._generate([prompt], stop=stop, run_manager=run_manager, **kwargs)
        return result.generations[0][0].text
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """异步单个调用 - 兼容旧版本接口"""
        result = await self._agenerate([prompt], stop=stop, run_manager=run_manager, **kwargs)
        return result.generations[0][0].text
    
    def invoke(
        self, 
        input: Union[PromptValue, str, Dict[str, Any]], 
        config: Optional[Dict] = None,
        **kwargs: Any
    ) -> str:
        """
        实现Runnable接口的invoke方法
        """
        if isinstance(input, PromptValue):
            prompt_str = input.to_string()
        elif isinstance(input, str):
            prompt_str = input
        elif isinstance(input, dict):
            # 处理字典格式的输入
            if 'input' in input:
                prompt_str = str(input['input'])
            elif 'question' in input:
                prompt_str = str(input['question'])
            else:
                prompt_str = str(input)
        else:
            prompt_str = str(input)
        
        return self._call(prompt_str, **kwargs)
    
    async def ainvoke(
        self, 
        input: Union[PromptValue, str, Dict[str, Any]], 
        config: Optional[Dict] = None,
        **kwargs: Any
    ) -> str:
        """
        实现Runnable接口的异步invoke方法
        """
        if isinstance(input, PromptValue):
            prompt_str = input.to_string()
        elif isinstance(input, str):
            prompt_str = input
        elif isinstance(input, dict):
            # 处理字典格式的输入
            if 'input' in input:
                prompt_str = str(input['input'])
            elif 'question' in input:
                prompt_str = str(input['question'])
            else:
                prompt_str = str(input)
        else:
            prompt_str = str(input)
        
        return await self._acall(prompt_str, **kwargs)
    
    def stream(
        self,
        input: Union[PromptValue, str, Dict[str, Any]],
        config: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """
        实现流式输出 - Runnable接口要求
        """
        # 对于通义千问，我们暂时不支持真正的流式输出
        # 直接返回完整结果
        result = self.invoke(input, config, **kwargs)
        yield result
    
    async def astream(
        self,
        input: Union[PromptValue, str, Dict[str, Any]],
        config: Optional[Dict] = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """
        实现异步流式输出 - Runnable接口要求
        """
        # 对于通义千问，我们暂时不支持真正的流式输出
        # 直接返回完整结果
        result = await self.ainvoke(input, config, **kwargs)
        yield result
    
    def batch(
        self,
        inputs: List[Union[PromptValue, str, Dict[str, Any]]],
        config: Optional[Union[Dict, List[Dict]]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        批量处理 - Runnable接口要求
        """
        results = []
        for input_item in inputs:
            result = self.invoke(input_item, config, **kwargs)
            results.append(result)
        return results
    
    async def abatch(
        self,
        inputs: List[Union[PromptValue, str, Dict[str, Any]]],
        config: Optional[Union[Dict, List[Dict]]] = None,
        **kwargs: Any,
    ) -> List[str]:
        """
        异步批量处理 - Runnable接口要求
        """
        results = []
        for input_item in inputs:
            result = await self.ainvoke(input_item, config, **kwargs)
            results.append(result)
        return results
    
    @property
    def InputType(self) -> type:
        """输入类型 - Runnable接口要求"""
        return Union[PromptValue, str, Dict[str, Any]]
    
    @property
    def OutputType(self) -> type:
        """输出类型 - Runnable接口要求"""
        return str
    
    def get_input_schema(self, config: Optional[Dict] = None) -> type:
        """获取输入模式 - Runnable接口要求"""
        return Union[PromptValue, str, Dict[str, Any]]
    
    def get_output_schema(self, config: Optional[Dict] = None) -> type:
        """获取输出模式 - Runnable接口要求"""
        return str

class QwenChatModel:
    """通义千问对话模型（支持对话格式）"""
    
    def __init__(self, model_name: str = "qwen-plus", **kwargs):
        self.model_name = model_name
        self.temperature = kwargs.get("temperature", 0.1)
        self.max_tokens = kwargs.get("max_tokens", 2000)
        self.top_p = kwargs.get("top_p", 0.8)
        
        # 设置API密钥
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("请设置DASHSCOPE_API_KEY环境变量")
        
        dashscope.api_key = api_key
    
    def predict(self, text: str) -> str:
        """预测方法，兼容LangChain接口"""
        return self._call_chat([{"role": "user", "content": text}])
    
    def invoke(self, prompt_value) -> str:
        """invoke方法，兼容LangChain新版本"""
        if hasattr(prompt_value, 'to_string'):
            text = prompt_value.to_string()
        elif isinstance(prompt_value, dict):
            # 处理格式化的提示词
            if 'context' in prompt_value and 'question' in prompt_value:
                text = f"基于以下文档内容：\n{prompt_value['context']}\n\n用户问题：{prompt_value['question']}\n\n请回答："
            else:
                text = str(prompt_value)
        else:
            text = str(prompt_value)
        
        return self.predict(text)
    
    def _call_chat(self, messages: List[Dict[str, str]]) -> str:
        """调用通义千问聊天API"""
        try:
            response = dashscope.Generation.call(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                result_format='message'
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                logger.error(f"通义千问聊天API调用失败: {response.message}")
                raise Exception(f"聊天API调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"通义千问聊天调用异常: {str(e)}")
            raise e
    
    @property
    def _llm_type(self) -> str:
        return "qwen" 