import os
import logging
from typing import Optional, Dict, Any
from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosClientError, CosServiceError
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class TencentCOSClient:
    """腾讯云对象存储客户端"""
    
    def __init__(self):
        """初始化腾讯云COS客户端"""
        # 从环境变量获取配置
        self.secret_id = os.getenv("TENCENT_SECRET_ID")
        self.secret_key = os.getenv("TENCENT_SECRET_KEY")
        self.region = os.getenv("TENCENT_COS_REGION", "ap-beijing")
        self.bucket_name = os.getenv("TENCENT_COS_BUCKET", "pdfrag-1304062057")
        
        if not self.secret_id or not self.secret_key:
            raise ValueError("请设置腾讯云密钥环境变量: TENCENT_SECRET_ID, TENCENT_SECRET_KEY")
        
        # 初始化COS配置
        config = CosConfig(
            Region=self.region,
            SecretId=self.secret_id,
            SecretKey=self.secret_key,
            Token=None,  # 如果使用临时密钥，需要传入Token
            Scheme="https"  # 使用HTTPS
        )
        
        self.client = CosS3Client(config)
        
        logger.info(f"腾讯云COS客户端初始化完成 - 区域: {self.region}, 存储桶: {self.bucket_name}")
    
    def upload_file(self, file_content: bytes, object_key: str, content_type: str = "application/pdf") -> Dict[str, Any]:
        """
        上传文件到腾讯云COS
        
        Args:
            file_content: 文件内容字节
            object_key: 对象键（文件在COS中的路径）
            content_type: 文件类型
            
        Returns:
            包含上传结果的字典
        """
        try:
            start_time = time.time()
            
            # 上传文件
            response = self.client.put_object(
                Bucket=self.bucket_name,
                Body=file_content,
                Key=object_key,
                ContentType=content_type,
                StorageClass='STANDARD',  # 标准存储
                Metadata={
                    'upload_time': datetime.now().isoformat(),
                    'file_size': str(len(file_content))
                }
            )
            
            upload_time = time.time() - start_time
            
            # 构建文件访问URL
            file_url = f"https://{self.bucket_name}.cos.{self.region}.myqcloud.com/{object_key}"
            
            result = {
                "success": True,
                "object_key": object_key,
                "file_url": file_url,
                "file_size": len(file_content),
                "upload_time": upload_time,
                "etag": response.get('ETag', '').strip('"'),
                "version_id": response.get('VersionId', ''),
                "error": None
            }
            
            logger.info(f"文件上传成功 - 对象键: {object_key}, 大小: {len(file_content)} bytes, 耗时: {upload_time:.2f}s")
            return result
            
        except CosClientError as e:
            error_msg = f"COS客户端错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "object_key": object_key,
                "file_url": None,
                "file_size": len(file_content),
                "upload_time": 0,
                "etag": None,
                "version_id": None,
                "error": error_msg
            }
            
        except CosServiceError as e:
            error_msg = f"COS服务错误: {e.get_error_code()} - {e.get_error_msg()}"
            logger.error(error_msg)
            return {
                "success": False,
                "object_key": object_key,
                "file_url": None,
                "file_size": len(file_content),
                "upload_time": 0,
                "etag": None,
                "version_id": None,
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "object_key": object_key,
                "file_url": None,
                "file_size": len(file_content),
                "upload_time": 0,
                "etag": None,
                "version_id": None,
                "error": error_msg
            }
    
    def download_file(self, object_key: str) -> Optional[bytes]:
        """
        从腾讯云COS下载文件 - 改进版，支持分块下载和完整性验证
        """
        try:
            # 首先获取文件信息以验证大小
            file_info = self.get_file_info(object_key)
            if not file_info:
                logger.error(f"无法获取文件信息: {object_key}")
                return None
                
            expected_size = file_info["file_size"]
            logger.info(f"开始下载文件 - 对象键: {object_key}, 预期大小: {expected_size} bytes")
            
            # 获取对象
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            # 分块读取文件内容，确保完整下载
            file_content = b""
            chunk_size = 64 * 1024  # 64KB 分块
            
            while True:
                chunk = response['Body'].read(chunk_size)
                if not chunk:
                    break
                file_content += chunk
                
            # 验证下载完整性
            actual_size = len(file_content)
            
            if actual_size != expected_size:
                logger.error(f"文件下载不完整 - 期望: {expected_size} bytes, 实际: {actual_size} bytes")
                return None
                
            logger.info(f"文件下载成功 - 对象键: {object_key}, 大小: {actual_size} bytes")
            return file_content
            
        except CosClientError as e:
            logger.error(f"COS客户端错误: {str(e)}")
            return None
            
        except CosServiceError as e:
            logger.error(f"COS服务错误: {e.get_error_code()} - {e.get_error_msg()}")
            return None
            
        except Exception as e:
            logger.error(f"下载文件失败: {str(e)}")
            return None
    
    def delete_file(self, object_key: str) -> bool:
        """
        删除腾讯云COS中的文件
        
        Args:
            object_key: 对象键
            
        Returns:
            删除是否成功
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"文件删除成功 - 对象键: {object_key}")
            return True
            
        except CosClientError as e:
            logger.error(f"COS客户端错误: {str(e)}")
            return False
            
        except CosServiceError as e:
            logger.error(f"COS服务错误: {e.get_error_code()} - {e.get_error_msg()}")
            return False
            
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            object_key: 对象键
            
        Returns:
            文件是否存在
        """
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
            
        except CosServiceError as e:
            if e.get_error_code() == 'NoSuchKey':
                return False
            logger.error(f"检查文件存在性失败: {e.get_error_code()} - {e.get_error_msg()}")
            return False
            
        except Exception as e:
            logger.error(f"检查文件存在性失败: {str(e)}")
            return False
    
    def get_file_info(self, object_key: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            object_key: 对象键
            
        Returns:
            文件信息字典，失败时返回None
        """
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return {
                "object_key": object_key,
                "file_size": int(response.get('Content-Length', 0)),
                "last_modified": response.get('Last-Modified', ''),
                "etag": response.get('ETag', '').strip('"'),
                "content_type": response.get('Content-Type', ''),
                "storage_class": response.get('x-cos-storage-class', 'STANDARD')
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return None
    
    def generate_presigned_url(self, object_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        生成预签名URL
        
        Args:
            object_key: 对象键
            expires_in: 过期时间（秒）
            
        Returns:
            预签名URL，失败时返回None
        """
        try:
            url = self.client.get_presigned_url(
                Method='GET',
                Bucket=self.bucket_name,
                Key=object_key,
                Expired=expires_in
            )
            
            logger.info(f"生成预签名URL成功 - 对象键: {object_key}, 有效期: {expires_in}秒")
            return url
            
        except Exception as e:
            logger.error(f"生成预签名URL失败: {str(e)}")
            return None

# 全局COS客户端实例
cos_client = None

def get_cos_client() -> TencentCOSClient:
    """获取COS客户端实例（单例模式）"""
    global cos_client
    if cos_client is None:
        cos_client = TencentCOSClient()
    return cos_client 