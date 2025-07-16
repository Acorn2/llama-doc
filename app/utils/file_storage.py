import os
import logging
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from .cos_client import get_cos_client

logger = logging.getLogger(__name__)

class StorageType(str, Enum):
    LOCAL = "local"
    COS = "cos"

class FileStorageManager:
    """文件存储管理器 - 支持本地和腾讯云COS"""
    
    def __init__(self):
        self.storage_type = os.getenv("FILE_STORAGE_TYPE", "local").lower()
        self.local_upload_dir = os.getenv("UPLOAD_DIRECTORY", "./uploads")
        
        # 确保本地上传目录存在
        os.makedirs(self.local_upload_dir, exist_ok=True)
        
        # 如果使用COS，初始化COS客户端
        if self.storage_type == StorageType.COS:
            try:
                self.cos_client = get_cos_client()
                logger.info("文件存储管理器初始化完成 - 使用腾讯云COS")
            except Exception as e:
                logger.error(f"COS客户端初始化失败: {e}")
                logger.info("降级到本地存储")
                self.storage_type = StorageType.LOCAL
        else:
            self.cos_client = None
            logger.info("文件存储管理器初始化完成 - 使用本地存储")
    
    def save_file(self, file_content: bytes, document_id: str, filename: str) -> Dict[str, Any]:
        """
        保存文件
        
        Args:
            file_content: 文件内容
            document_id: 文档ID
            filename: 原始文件名
            
        Returns:
            保存结果字典
        """
        if self.storage_type == StorageType.COS:
            return self._save_to_cos(file_content, document_id, filename)
        else:
            return self._save_to_local(file_content, document_id, filename)
    
    def _save_to_cos(self, file_content: bytes, document_id: str, filename: str) -> Dict[str, Any]:
        """保存文件到腾讯云COS"""
        try:
            # 构建COS对象键：documents/{document_id}.pdf
            object_key = f"documents/{document_id}.pdf"
            
            # 上传到COS
            result = self.cos_client.upload_file(
                file_content=file_content,
                object_key=object_key,
                content_type="application/pdf"
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "storage_type": StorageType.COS,
                    "file_path": result["file_url"],  # COS URL作为文件路径
                    "cos_object_key": object_key,
                    "cos_file_url": result["file_url"],
                    "cos_etag": result["etag"],
                    "file_size": result["file_size"],
                    "error": None
                }
            else:
                # COS上传失败，降级到本地存储
                logger.warning(f"COS上传失败，降级到本地存储: {result['error']}")
                return self._save_to_local(file_content, document_id, filename)
                
        except Exception as e:
            logger.error(f"COS保存失败: {str(e)}")
            # 降级到本地存储
            return self._save_to_local(file_content, document_id, filename)
    
    def _save_to_local(self, file_content: bytes, document_id: str, filename: str) -> Dict[str, Any]:
        """保存文件到本地"""
        try:
            # 构建本地文件路径
            local_path = os.path.join(self.local_upload_dir, f"{document_id}.pdf")
            
            # 写入文件
            with open(local_path, "wb") as f:
                f.write(file_content)
            
            return {
                "success": True,
                "storage_type": StorageType.LOCAL,
                "file_path": local_path,
                "cos_object_key": None,
                "cos_file_url": None,
                "cos_etag": None,
                "file_size": len(file_content),
                "error": None
            }
            
        except Exception as e:
            error_msg = f"本地保存失败: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "storage_type": StorageType.LOCAL,
                "file_path": None,
                "cos_object_key": None,
                "cos_file_url": None,
                "cos_etag": None,
                "file_size": len(file_content),
                "error": error_msg
            }
    
    def get_file_content(self, document_id: str, storage_type: str, file_path: str, cos_object_key: str = None) -> Optional[bytes]:
        """
        获取文件内容
        
        Args:
            document_id: 文档ID
            storage_type: 存储类型
            file_path: 文件路径（本地）或URL（COS）
            cos_object_key: COS对象键
            
        Returns:
            文件内容字节，失败时返回None
        """
        if storage_type == StorageType.COS and cos_object_key:
            return self._get_from_cos(cos_object_key)
        else:
            return self._get_from_local(file_path)
    
    def _get_from_cos(self, object_key: str) -> Optional[bytes]:
        """从COS获取文件内容"""
        try:
            if not self.cos_client:
                self.cos_client = get_cos_client()
            
            return self.cos_client.download_file(object_key)
            
        except Exception as e:
            logger.error(f"从COS获取文件失败: {str(e)}")
            return None
    
    def _get_from_local(self, file_path: str) -> Optional[bytes]:
        """从本地获取文件内容"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"本地文件不存在: {file_path}")
                return None
            
            with open(file_path, "rb") as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"读取本地文件失败: {str(e)}")
            return None
    
    def delete_file(self, document_id: str, storage_type: str, file_path: str, cos_object_key: str = None) -> bool:
        """
        删除文件
        
        Args:
            document_id: 文档ID
            storage_type: 存储类型
            file_path: 文件路径
            cos_object_key: COS对象键
            
        Returns:
            删除是否成功
        """
        if storage_type == StorageType.COS and cos_object_key:
            return self._delete_from_cos(cos_object_key)
        else:
            return self._delete_from_local(file_path)
    
    def _delete_from_cos(self, object_key: str) -> bool:
        """从COS删除文件"""
        try:
            if not self.cos_client:
                self.cos_client = get_cos_client()
            
            return self.cos_client.delete_file(object_key)
            
        except Exception as e:
            logger.error(f"从COS删除文件失败: {str(e)}")
            return False
    
    def _delete_from_local(self, file_path: str) -> bool:
        """删除本地文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            else:
                logger.warning(f"本地文件不存在: {file_path}")
                return True  # 文件不存在也算删除成功
                
        except Exception as e:
            logger.error(f"删除本地文件失败: {str(e)}")
            return False
    
    def get_file_url(self, document_id: str, storage_type: str, file_path: str, cos_object_key: str = None) -> Optional[str]:
        """
        获取文件访问URL
        
        Args:
            document_id: 文档ID
            storage_type: 存储类型
            file_path: 文件路径
            cos_object_key: COS对象键
            
        Returns:
            文件访问URL，失败时返回None
        """
        if storage_type == StorageType.COS and cos_object_key:
            try:
                if not self.cos_client:
                    self.cos_client = get_cos_client()
                
                # 生成1小时有效期的预签名URL
                return self.cos_client.generate_presigned_url(cos_object_key, expires_in=3600)
                
            except Exception as e:
                logger.error(f"生成COS预签名URL失败: {str(e)}")
                return None
        else:
            # 本地文件不支持直接URL访问
            return None

# 全局文件存储管理器实例
file_storage_manager = FileStorageManager() 