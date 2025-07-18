"""
错误处理中间件
统一处理应用中的异常
"""

import logging
import time
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.exceptions import BaseAppException

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并捕获异常"""
        start_time = time.time()
        request_id = id(request)
        
        try:
            # 记录请求开始
            logger.info(
                f"请求开始 - ID: {request_id}, "
                f"方法: {request.method}, "
                f"路径: {request.url.path}"
            )
            
            # 执行请求
            response = await call_next(request)
            
            # 记录请求完成
            process_time = time.time() - start_time
            logger.info(
                f"请求完成 - ID: {request_id}, "
                f"状态码: {response.status_code}, "
                f"耗时: {process_time:.3f}s"
            )
            
            return response
            
        except BaseAppException as e:
            # 处理应用自定义异常
            process_time = time.time() - start_time
            logger.error(
                f"应用异常 - ID: {request_id}, "
                f"错误: {e.message}, "
                f"错误码: {e.error_code}, "
                f"耗时: {process_time:.3f}s"
            )
            
            return self._create_error_response(
                request_id=request_id,
                error_code=e.error_code,
                message=e.message,
                details=e.details,
                status_code=self._get_status_code_for_error(e.error_code)
            )
            
        except Exception as e:
            # 处理未预期的异常
            process_time = time.time() - start_time
            logger.error(
                f"未处理异常 - ID: {request_id}, "
                f"错误: {str(e)}, "
                f"耗时: {process_time:.3f}s",
                exc_info=True
            )
            
            return self._create_error_response(
                request_id=request_id,
                error_code="INTERNAL_SERVER_ERROR",
                message="服务器内部错误",
                details={"trace_id": str(request_id)},
                status_code=500
            )
    
    def _get_status_code_for_error(self, error_code: str) -> int:
        """根据错误码获取HTTP状态码"""
        status_map = {
            "KB_NOT_FOUND": 404,
            "VALIDATION_ERROR": 400,
            "AGENT_ERROR": 500,
            "DOC_PROCESSING_ERROR": 500,
            "LLM_ERROR": 500,
            "VECTOR_STORE_ERROR": 500,
        }
        return status_map.get(error_code, 500)
    
    def _create_error_response(
        self,
        request_id: int,
        error_code: str,
        message: str,
        details: dict,
        status_code: int
    ) -> JSONResponse:
        """创建错误响应"""
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": details,
                    "request_id": str(request_id),
                    "timestamp": time.time()
                }
            }
        )