"""
全局异常处理器
"""

import logging
from typing import Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from json import JSONDecodeError

from app.utils.exceptions import BaseAppException

logger = logging.getLogger(__name__)


async def base_app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """
    处理应用自定义异常
    """
    logger.error(f"应用异常: {exc.message} - 错误码: {exc.error_code}")
    
    # 根据错误类型确定HTTP状态码
    status_code_map = {
        "KB_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "AGENT_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "DOC_PROCESSING_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "LLM_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "VECTOR_STORE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    status_code = status_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            },
            "path": str(request.url),
            "method": request.method
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    处理HTTP异常
    """
    logger.error(f"HTTP异常: {exc.detail} - 状态码: {exc.status_code}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": {}
            },
            "path": str(request.url),
            "method": request.method
        }
    )


async def json_decode_exception_handler(request: Request, exc: JSONDecodeError) -> JSONResponse:
    """
    处理JSON解析异常
    """
    logger.error(f"JSON解析异常: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": "JSON_DECODE_ERROR",
                "message": "JSON格式错误，请检查请求体格式",
                "details": {
                    "error": str(exc),
                    "position": exc.pos if hasattr(exc, 'pos') else None,
                    "hint": "请确保JSON格式正确，不要有多余的逗号"
                }
            },
            "path": str(request.url),
            "method": request.method
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    处理请求验证异常
    """
    logger.error(f"请求验证异常: {exc.errors()}")
    
    # 检查是否是JSON解析错误
    for error in exc.errors():
        if error.get('type') == 'json_invalid':
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": {
                        "code": "JSON_DECODE_ERROR",
                        "message": "JSON格式错误，请检查请求体格式",
                        "details": {
                            "error": error.get('msg', ''),
                            "location": error.get('loc', []),
                            "hint": "请确保JSON格式正确，不要有多余的逗号或引号"
                        }
                    },
                    "path": str(request.url),
                    "method": request.method
                }
            )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数验证失败",
                "details": {
                    "validation_errors": exc.errors()
                }
            },
            "path": str(request.url),
            "method": request.method
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    处理未捕获的异常
    """
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
                "details": {}
            },
            "path": str(request.url),
            "method": request.method
        }
    )


def register_exception_handlers(app):
    """
    注册异常处理器
    """
    app.add_exception_handler(BaseAppException, base_app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(JSONDecodeError, json_decode_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)