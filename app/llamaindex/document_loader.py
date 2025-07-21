"""
自定义文档加载器 - 支持多种文件格式
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import Document
from app.core.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

class CustomDocumentReader:
    """自定义文档加载器，支持PDF、TXT、DOC、DOCX文件"""
    
    def __init__(self):
        self.doc_processor = DocumentProcessor()
    
    def load_data(self, file_path: str) -> List[Document]:
        """
        加载文档文件并返回Document列表
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Document]: LlamaIndex Document对象列表
        """
        logger.info(f"使用通用文档处理器加载文件: {file_path}")
        
        try:
            documents = self.doc_processor.load_data(file_path)
            logger.info(f"成功加载文档，共{len(documents)}个文档片段")
            return documents
        except Exception as e:
            logger.error(f"加载文档文件失败: {str(e)}")
            raise
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        提取文件的元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 元数据字典
        """
        return self.doc_processor.extract_metadata(file_path)

# 保持向后兼容性
class CustomPDFReader(CustomDocumentReader):
    """PDF文档加载器 - 保持向后兼容"""
    pass 