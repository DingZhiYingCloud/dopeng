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


@require_GET
def index(request):
    # ---- 1. 获取二级域名前缀 ----
    subdomain = request_info.get_subdomain_prefix(request, main_domain)
    logger.info("请求二级域名前缀: %r", subdomain)

    # ---- 2. 识别是否来自搜索引擎蜘蛛 ----
    result = cloak_detector.detect_from_environ(request.META)
    logger.info(
        "蜘蛛检测结果: is_spider=%s, is_from_search_engine=%s, "
        "matched_spider=%s, matched_engine=%s",
        result.is_spider,
        result.is_from_search_engine,
        result.matched_spider,
        result.matched_engine,
    )

    # ---- 3. 根据检测结果分流 ----
    template_name = _get_template_name(subdomain)

    # 3a. 爬虫请求 → 直接渲染模板
    if result.is_spider:
        logger.info("爬虫请求，渲染模板: %s (subdomain=%r)", template_name, subdomain)
        return render(request, template_name)

    # 3b. 来自搜索引擎的真人请求 → 仅中文语言返回模板，否则重定向
    if result.is_from_search_engine:
        if _accept_language_is_chinese(request):
            logger.info(
                "搜索引擎真人请求(中文)，渲染模板: %s (subdomain=%r)",
                template_name, subdomain,
            )
            return render(request, template_name)
        else:
            logger.info("搜索引擎真人请求(非中文)，302 重定向至雅虎搜索")
            return _redirect_to_yahoo()

    # 3c. 其余所有请求 → 重定向
    logger.info("普通请求，302 重定向至雅虎搜索")
    return _redirect_to_yahoo()
