import hashlib
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def calculate_file_md5(file_path: str, chunk_size: int = 8192) -> Optional[str]:
    """
    计算文件的MD5哈希值
    
    Args:
        file_path: 文件路径
        chunk_size: 读取块大小，默认8KB
        
    Returns:
        MD5哈希值字符串，失败时返回None
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
            
        md5_hash = hashlib.md5()
        
        with open(file_path, "rb") as f:
            # 分块读取文件以处理大文件
            for chunk in iter(lambda: f.read(chunk_size), b""):
                md5_hash.update(chunk)
        
        return md5_hash.hexdigest()
        
    except Exception as e:
        logger.error(f"计算文件MD5失败 {file_path}: {str(e)}")
        return None

def calculate_content_md5(content: bytes) -> str:
    """
    计算内容的MD5哈希值
    
    Args:
        content: 文件内容字节
        
    Returns:
        MD5哈希值字符串
    """
    try:
        md5_hash = hashlib.md5()
        md5_hash.update(content)
        return md5_hash.hexdigest()
    except Exception as e:
        logger.error(f"计算内容MD5失败: {str(e)}")
        raise e

def is_duplicate_file(db, file_md5: str, exclude_doc_id: str = None) -> Optional[str]:
    """
    检查是否存在相同MD5的文件
    
    Args:
        db: 数据库会话
        file_md5: 文件MD5值
        exclude_doc_id: 排除的文档ID（用于更新场景）
        
    Returns:
        如果存在重复，返回已存在的文档ID；否则返回None
    """
    from ..database import Document
    
    try:
        query = db.query(Document).filter(Document.file_md5 == file_md5)
        
        if exclude_doc_id:
            query = query.filter(Document.id != exclude_doc_id)
            
        existing_doc = query.first()
        
        if existing_doc:
            return existing_doc.id
            
        return None
        
    except Exception as e:
        logger.error(f"检查重复文件失败: {str(e)}")
        return None 