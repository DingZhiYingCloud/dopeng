
from __future__ import annotations

from django.http import HttpRequest
from urllib.parse import urlparse

def get_subdomain_prefix(request: HttpRequest, main_domain: str) -> str:
    """
    提取当前请求域名的子域名前缀（主域名前面所有层级）
    :param request: django HttpRequest 对象
    :param main_domain: 基础主域名，如 "domain.com"
    :return: 子域前缀，无子域返回空字符串
    """
    # 获取原始HOST，处理反向代理 X-Forwarded-Host
    host = request.META.get("HTTP_X_FORWARDED_HOST", request.META.get("HTTP_HOST", ""))
    if not host:
        return ""

    # 去除端口号
    host = host.split(":")[0].strip().lower()
    main_domain = main_domain.strip().lower()

    # 判断是否以主域名结尾
    if not host.endswith(f".{main_domain}") and host != main_domain:
        return ""

    # 完全匹配主域名，没有子域
    if host == main_domain:
        return ""

    # 切掉末尾主域名，得到子域部分
    sub_part = host[:-(len(main_domain) + 1)]
    return sub_part

# HTTP/HTTPS 之外的协议头一律忽略,避免被请求头污染
_VALID_PROTOCOLS: tuple[str, ...] = ("http", "https")


def get_current_domain(request: HttpRequest, with_protocol: bool = False) -> str:
    """
    获取当前请求的**主域**(含端口),根据 ``with_protocol`` 决定是否带协议头。

    协议判定顺序
    ------------
    1. ``request.is_secure()`` —— Django 自带的 HTTPS 判定
       (会读 ``request.scheme`` / ``SECURE_PROXY_SSL_HEADER`` 配置)
    2. 反向代理若**没**配 ``SECURE_PROXY_SSL_HEADER``,回退到 ``X-Forwarded-Proto`` 头
    3. 都没匹配上时按 ``http`` 处理

    主机名取值
    ---------
    使用 ``request.get_host()``,自动处理 ``HTTP_HOST`` / ``SERVER_NAME`` /
    ``ALLOWED_HOSTS`` 校验,比直接读 ``META`` 更安全。

    参数
    ----
    request : HttpRequest
        Django 请求对象。
    with_protocol : bool
        是否在结果前加 ``http://`` / ``https://``(默认 ``False``)。

    返回
    ----
    str
        - ``with_protocol=False`` -> ``"example.com"`` 或 ``"example.com:8000"``
        - ``with_protocol=True``  -> ``"https://example.com"`` 或 ``"https://example.com:8000"``

    示例
    ----
    >>> # 普通 HTTP 请求
    >>> get_current_domain(request, with_protocol=True)
    'http://example.com:8000'

    >>> # Nginx 反向代理,客户端走 HTTPS 但没配 SECURE_PROXY_SSL_HEADER
    >>> # 此时 is_secure()=False,但 X-Forwarded-Proto="https"
    >>> get_current_domain(request, with_protocol=True)
    'https://example.com'

    异常
    ----
    ``django.core.exceptions.DisallowedHost``
        ``ALLOWED_HOSTS`` 没配好时,``get_host()`` 会抛这个异常,
        本函数不捕获,由调用方决定如何处理。
    """
    # 1. 协议:优先用 Django 的 is_secure()(兼容性最好)
    if request.is_secure():
        scheme = "https"
    else:
        # 反向代理没配 SECURE_PROXY_SSL_HEADER 时的兜底
        scheme = "http"
        forwarded = request.META.get("HTTP_X_FORWARDED_PROTO", "").strip().lower()
        if forwarded in _VALID_PROTOCOLS:
            scheme = forwarded

    # 2. 主机(由 Django 做 ALLOWED_HOSTS 校验)
    host = request.get_host()

    # 3. 拼接
    return f"{scheme}://{host}" if with_protocol else host



