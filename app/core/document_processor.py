"""
通用文档处理器
支持PDF、TXT、DOC、DOCX文件的处理
"""
import logging
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from llama_index.core.schema import Document
from llama_index.readers.file import PyMuPDFReader
from llama_index.core import SimpleDirectoryReader

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """通用文档处理器，支持多种文件格式"""
    
    # 支持的文件类型及其MIME类型
    SUPPORTED_TYPES = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    def __init__(self):
        self.pdf_reader = PyMuPDFReader()
    
    def is_supported_file(self, filename: str) -> bool:
        """检查文件是否支持"""
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.SUPPORTED_TYPES
    
    def get_content_type(self, filename: str) -> str:
        """获取文件的MIME类型"""
        file_ext = Path(filename).suffix.lower()
        return self.SUPPORTED_TYPES.get(file_ext, 'application/octet-stream')
    
    def load_data(self, file_path: str) -> List[Document]:
        """
        加载文档并返回Document列表
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Document]: LlamaIndex Document对象列表
        """
        file_ext = Path(file_path).suffix.lower()
        logger.info(f"处理文件: {file_path}, 类型: {file_ext}")
        
        try:
            if file_ext == '.pdf':
                return self._load_pdf(file_path)
            elif file_ext == '.txt':
                return self._load_txt(file_path)
            elif file_ext in ['.doc', '.docx']:
                return self._load_word(file_path)
            else:
                raise ValueError(f"不支持的文件类型: {file_ext}")
        except Exception as e:
            logger.error(f"加载文件失败: {str(e)}")
            raise
    
    def _load_pdf(self, file_path: str) -> List[Document]:
        """加载PDF文件"""
        documents = self.pdf_reader.load_data(file_path)
        logger.info(f"成功加载PDF文档，共{len(documents)}个文档片段")
        return documents
    
    def _load_txt(self, file_path: str) -> List[Document]:
        """加载TXT文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        # 创建Document对象
        document = Document(
            text=content,
            metadata={
                'file_name': os.path.basename(file_path),
                'file_type': 'txt',
                'file_size': os.path.getsize(file_path)
            }
        )
        
        logger.info(f"成功加载TXT文档，内容长度: {len(content)}")
        return [document]
    
    def _load_word(self, file_path: str) -> List[Document]:
        """加载DOC/DOCX文件"""
        try:
            import docx
            from docx import Document as DocxDocument
        except ImportError:
            raise ImportError("需要安装python-docx库来处理Word文档: pip install python-docx")
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.docx':
            return self._load_docx(file_path)
        elif file_ext == '.doc':
            return self._load_doc(file_path)
    
    def _load_docx(self, file_path: str) -> List[Document]:
        """加载DOCX文件"""
        try:
            import docx
        except ImportError:
            raise ImportError("需要安装python-docx库: pip install python-docx")
        
        doc = docx.Document(file_path)
        
        # 提取所有段落文本
        paragraphs = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text.strip())
        
        content = '\n'.join(paragraphs)
        
        # 创建Document对象
        document = Document(
            text=content,
            metadata={
                'file_name': os.path.basename(file_path),
                'file_type': 'docx',
                'file_size': os.path.getsize(file_path),
                'paragraphs_count': len(paragraphs)
            }
        )
        
        logger.info(f"成功加载DOCX文档，段落数: {len(paragraphs)}")
        return [document]
    
    def _load_doc(self, file_path: str) -> List[Document]:
        """加载DOC文件"""
        try:
            import win32com.client
        except ImportError:
            # 如果没有win32com，尝试使用python-docx2txt
            try:
                import docx2txt
                content = docx2txt.process(file_path)
            except ImportError:
                raise ImportError("处理.doc文件需要安装docx2txt库: pip install docx2txt")
        else:
            # 使用win32com处理（仅Windows）
            word = win32com.client.Dispatch("Word.Application")
            word.visible = False
            doc = word.Documents.Open(file_path)
            content = doc.Content.Text
            doc.Close()
            word.Quit()
        
        # 创建Document对象
        document = Document(
            text=content,
            metadata={
                'file_name': os.path.basename(file_path),
                'file_type': 'doc',
                'file_size': os.path.getsize(file_path)
            }
        )
        
        logger.info(f"成功加载DOC文档，内容长度: {len(content)}")
        return [document]
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        提取文件的元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 元数据字典
        """
        file_ext = Path(file_path).suffix.lower()
        
        # 基础元数据
        metadata = {
            'file_name': os.path.basename(file_path),
            'file_type': file_ext[1:],  # 去掉点号
            'file_size': os.path.getsize(file_path),
            'file_path': file_path
        }
        
        try:
            if file_ext == '.pdf':
                metadata.update(self._extract_pdf_metadata(file_path))
            elif file_ext == '.docx':
                metadata.update(self._extract_docx_metadata(file_path))
            # TXT和DOC文件的元数据较少，使用基础元数据即可
        except Exception as e:
            logger.warning(f"提取元数据失败: {str(e)}")
        
        return metadata
    
    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取PDF元数据"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(file_path)
            metadata = doc.metadata
            
            return {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'creation_date': metadata.get('creationDate', ''),
                'modification_date': metadata.get('modDate', ''),
                'pages': doc.page_count
            }
        except Exception as e:
            logger.error(f"提取PDF元数据失败: {str(e)}")
            return {}
    
    def _extract_docx_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取DOCX元数据"""
        try:
            import docx
            
            doc = docx.Document(file_path)
            core_props = doc.core_properties
            
            return {
                'title': core_props.title or '',
                'author': core_props.author or '',
                'subject': core_props.subject or '',
                'creator': core_props.author or '',
                'creation_date': core_props.created.isoformat() if core_props.created else '',
                'modification_date': core_props.modified.isoformat() if core_props.modified else '',
                'paragraphs': len(doc.paragraphs)
            }
        except Exception as e:
            logger.error(f"提取DOCX元数据失败: {str(e)}")
            return {}