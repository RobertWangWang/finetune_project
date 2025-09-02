import json

from fastapi import Request
from fastapi.openapi.models import Response
from starlette.responses import JSONResponse, StreamingResponse

from app.api.middleware.context import set_current_locale


async def i18n_middleware(request: Request, call_next):
    # 从请求中提取语言设置 (支持多种方式)
    locale = extract_locale_from_request(request)

    # 设置到协程局部变量中
    set_current_locale(locale)

    try:
        response = await call_next(request)
    finally:
        # 清理工作 (可选)
        pass

    return response


async def wrap_response_middleware(request: Request, call_next):
    # 调用后续中间件和路由处理
    response = await call_next(request)

    if response.status_code >= 400:
        return response


    # 只处理JSON响应（可根据需求调整）
    if response.headers.get("content-type") == "application/json":
        # 获取原始响应体
        raw_body = b""
        async for chunk in response.body_iterator:
            raw_body += chunk

        # 解析原始JSON
        original_data = json.loads(raw_body)

        # 包装成 { data: ... } 格式
        wrapped_data = {"data": original_data, "code": response.status_code}

        # 创建新响应
        return JSONResponse(
            content=wrapped_data,
            status_code=response.status_code,
        )

    return response


def extract_locale_from_request(request: Request) -> str:
    """从请求中提取语言设置"""
    # 1. 检查查询参数
    if "lang" in request.query_params:
        return request.query_params["lang"]

    # 2. 检查Accept-Language头部
    accept_language = request.headers.get("accept-language", "zh")
    lang = accept_language.split(",")[0].split("-")[0].lower()

    # 支持的语言列表
    supported_languages = ["en", "zh"]
    return lang if lang in supported_languages else "zh"
