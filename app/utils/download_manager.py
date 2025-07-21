"""
文件下载管理器
支持多种文件类型的下载链接生成
"""
import logging
from typing import Dict, Any, Optional
from .file_storage import file_storage_manager, StorageType

logger = logging.getLogger(__name__)

class DownloadManager:
    """文件下载管理器"""
    
    def __init__(self):
        self.storage_manager = file_storage_manager
    
    def get_download_url(
        self, 
        document_id: str, 
        storage_type: str, 
        file_path: str, 
        cos_object_key: Optional[str] = None,
        filename: str = "document"
    ) -> Dict[str, Any]:
        """
        获取文件下载URL
        
        Args:
            document_id: 文档ID
            storage_type: 存储类型
            file_path: 文件路径
            cos_object_key: COS对象键
            filename: 原始文件名
            
        Returns:
            下载信息字典
        """
        try:
            if storage_type == StorageType.COS and cos_object_key:
                return self._get_cos_download_url(cos_object_key, filename)
            else:
                return self._get_local_download_info(file_path, filename)
        except Exception as e:
            logger.error(f"获取下载URL失败: {str(e)}")
            return {
                "success": False,
                "download_url": None,
                "expires": None,
                "error": str(e)
            }
    
    def _get_cos_download_url(self, object_key: str, filename: str) -> Dict[str, Any]:
        """获取COS文件下载URL"""
        try:
            # 生成预签名URL，有效期1小时
            download_url = self.storage_manager.cos_client.generate_presigned_url(
                object_key, 
                expires_in=3600
            )
            
            if download_url:
                return {
                    "success": True,
                    "download_url": download_url,
                    "expires": "1小时",
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "download_url": None,
                    "expires": None,
                    "error": "生成预签名URL失败"
                }
        except Exception as e:
            logger.error(f"生成COS下载URL失败: {str(e)}")
            return {
                "success": False,
                "download_url": None,
                "expires": None,
                "error": str(e)
            }
    
    def _get_local_download_info(self, file_path: str, filename: str) -> Dict[str, Any]:
        """获取本地文件下载信息"""
        import os
        
        try:
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "download_url": None,
                    "expires": None,
                    "error": "文件不存在"
                }
            
            # 本地文件通过API端点提供下载
            # 这里返回一个相对路径，实际的下载会通过API处理
            return {
                "success": True,
                "download_url": f"/api/v1/documents/download/local/{os.path.basename(file_path)}",
                "expires": "永久有效",
                "error": None
            }
        except Exception as e:
            logger.error(f"获取本地文件下载信息失败: {str(e)}")
            return {
                "success": False,
                "download_url": None,
                "expires": None,
                "error": str(e)
            }

# 全局下载管理器实例
download_manager = DownloadManager()