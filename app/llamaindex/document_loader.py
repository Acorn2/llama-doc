"""
自定义文档加载器，基于LlamaIndex的SimpleDirectoryReader
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import Document
from llama_index.readers.file import PyMuPDFReader

logger = logging.getLogger(__name__)

class CustomPDFReader:
    """自定义PDF文档加载器，基于LlamaIndex的PyMuPDFReader"""
    
    def __init__(self):
        self.pdf_reader = PyMuPDFReader()
    
    def load_data(self, file_path: str) -> List[Document]:
        """
        加载PDF文件并返回Document列表
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            List[Document]: LlamaIndex Document对象列表
        """
        logger.info(f"使用LlamaIndex加载PDF文件: {file_path}")
        try:
            documents = self.pdf_reader.load_data(file_path)
            logger.info(f"成功加载文档，共{len(documents)}个文档片段")
            return documents
        except Exception as e:
            logger.error(f"加载PDF文件失败: {str(e)}")
            raise
    
    @staticmethod
    def extract_metadata(file_path: str) -> Dict[str, Any]:
        """
        提取PDF文件的元数据
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            Dict[str, Any]: 元数据字典
        """
        import fitz  # PyMuPDF
        
        metadata = {}
        try:
            with fitz.open(file_path) as doc:
                metadata = {
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "subject": doc.metadata.get("subject", ""),
                    "keywords": doc.metadata.get("keywords", ""),
                    "creator": doc.metadata.get("creator", ""),
                    "producer": doc.metadata.get("producer", ""),
                    "page_count": len(doc),
                    "file_size": Path(file_path).stat().st_size
                }
        except Exception as e:
            logger.error(f"提取PDF元数据失败: {str(e)}")
        
        return metadata 