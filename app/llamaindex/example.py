"""
LlamaIndex集成示例脚本
"""
import os
import logging
import argparse
from dotenv import load_dotenv

from app.llamaindex.adapter import LlamaIndexAdapter
from app.llamaindex.qwen_integration import QwenLlamaLLM, QwenLlamaEmbedding
from llama_index.core import Settings

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

def setup_llamaindex_with_qwen():
    """设置使用通义千问的LlamaIndex"""
    # 检查API密钥
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("请设置DASHSCOPE_API_KEY环境变量")
    
    # 创建通义千问LLM和嵌入模型
    llm = QwenLlamaLLM(model_name="qwen-max", api_key=api_key)
    embed_model = QwenLlamaEmbedding(model_name="text-embedding-v1", api_key=api_key)
    
    # 配置LlamaIndex全局设置
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.chunk_size = 512
    Settings.chunk_overlap = 50
    
    logger.info("已配置LlamaIndex使用通义千问模型")

def process_document(file_path: str):
    """处理文档示例"""
    # 创建适配器
    adapter = LlamaIndexAdapter(
        embedding_model_name="text-embedding-v1",  # 使用通义千问嵌入模型
        llm_model_name="qwen-max",  # 使用通义千问LLM
        chunk_size=512,
        chunk_overlap=50
    )
    
    # 上传并处理文档
    document_id = adapter.upload_and_process_document(file_path)
    if document_id:
        logger.info(f"文档处理成功，ID: {document_id}")
        return document_id
    else:
        logger.error("文档处理失败")
        return None

def query_document(document_id: str, query_text: str):
    """查询文档示例"""
    # 创建适配器
    adapter = LlamaIndexAdapter(
        embedding_model_name="text-embedding-v1",
        llm_model_name="qwen-max",
        similarity_top_k=3
    )
    
    # 查询文档
    response, source_nodes = adapter.query_document(document_id, query_text)
    
    # 打印结果
    logger.info(f"查询: {query_text}")
    logger.info(f"回答: {response}")
    logger.info(f"相关文档片段数量: {len(source_nodes)}")
    
    # 打印相关文档片段
    for i, node in enumerate(source_nodes):
        logger.info(f"片段 {i+1}:")
        logger.info(f"相似度: {node.get('score')}")
        logger.info(f"内容: {node.get('text')[:100]}...")
    
    return response

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LlamaIndex集成示例")
    parser.add_argument("--action", choices=["process", "query"], required=True, help="操作类型：处理文档或查询文档")
    parser.add_argument("--file", help="PDF文件路径，用于处理文档")
    parser.add_argument("--doc_id", help="文档ID，用于查询文档")
    parser.add_argument("--query", help="查询文本，用于查询文档")
    
    args = parser.parse_args()
    
    # 设置LlamaIndex使用通义千问
    setup_llamaindex_with_qwen()
    
    if args.action == "process":
        if not args.file:
            parser.error("处理文档需要提供--file参数")
        process_document(args.file)
    
    elif args.action == "query":
        if not args.doc_id or not args.query:
            parser.error("查询文档需要提供--doc_id和--query参数")
        query_document(args.doc_id, args.query)

if __name__ == "__main__":
    main() 