import contextvars

# 创建协程局部变量
request_locale = contextvars.ContextVar("request_locale", default="zh")


def get_current_locale() -> str:
    """获取当前协程的locale设置"""
    return request_locale.get()


def set_current_locale(locale: str):
    """设置当前协程的locale"""
    request_locale.set(locale)
