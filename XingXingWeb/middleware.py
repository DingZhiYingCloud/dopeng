import logging

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from XingXingWeb.models import RequestLog
from XingXingWeb.utils import cloak_detect, request_info

logger = logging.getLogger(__name__)

cloak_detector = cloak_detect.CloakDetector()


class RequestLogMiddleware(MiddlewareMixin):
    """
    记录所有请求信息到 RequestLog 模型。
    放在中间件末尾，确保能捕获 response 的状态码。
    """

    def process_response(self, request, response):
        # 跳过静态文件和媒体文件请求，减少脏数据
        path = request.path
        if path.startswith("/static/") or path.startswith("/media/"):
            return response

        try:
            # 基础信息
            ip = request.META.get("HTTP_X_FORWARDED_FOR", "") or request.META.get("REMOTE_ADDR", "") or ""
            if ip and "," in ip:
                ip = ip.split(",")[0].strip()

            host = request.META.get("HTTP_HOST", "")
            subdomain = ""
            main_domain = getattr(settings, "MAIN_DOMAIN", "")
            if main_domain:
                subdomain = request_info.get_subdomain_prefix(request, main_domain)

            # 爬虫/搜索引擎检测
            result = cloak_detector.detect_from_environ(request.META)

            # 响应模板（从 response 上下文或属性中提取）
            response_template = ""
            if hasattr(response, "template_name"):
                response_template = str(response.template_name)
            elif getattr(response, "status_code", None) == 302:
                response_template = "redirect"
            elif getattr(response, "status_code", None) == 200:
                response_template = "direct_response"

            # 设置 Referer 小写化存储
            referer = request.META.get("HTTP_REFERER", "")

            RequestLog.objects.create(
                ip=ip,
                method=request.method,
                path=path,
                full_path=request.get_full_path(),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                referer=referer,
                accept_language=request.META.get("HTTP_ACCEPT_LANGUAGE", ""),
                accept_encoding=request.META.get("HTTP_ACCEPT_ENCODING", ""),
                host=host,
                subdomain=subdomain,
                is_spider=result.is_spider,
                matched_spider=result.matched_spider or "",
                is_from_search_engine=result.is_from_search_engine,
                matched_engine=result.matched_engine or "",
                status_code=getattr(response, "status_code", None),
                response_template=response_template,
            )
        except Exception as e:
            logger.warning("记录请求日志失败: %s", e)

        return response
