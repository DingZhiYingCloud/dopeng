from datetime import datetime, date

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render

from XingXingWeb.models import RequestLog


def stats(request):
    """
    访问统计页面，支持搜索、筛选、分页。
    """
    # ---- 读取筛选参数 ----
    q = request.GET.get("q", "").strip()              # 全文搜索：IP / 路径 / Host / UA / Referer
    log_type = request.GET.get("type", "").strip()     # spider / engine / normal
    status_code = request.GET.get("status", "").strip()  # 200 / 302 / 其它数字
    subdomain = request.GET.get("subdomain", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    page = request.GET.get("page", 1)
    page_size = _parse_page_size(request.GET.get("page_size", "50"))

    # ---- 构建查询集 ----
    qs = RequestLog.objects.all()

    # 关键词搜索（在多个字段中模糊匹配）
    if q:
        qs = qs.filter(
            Q(ip__icontains=q) |
            Q(path__icontains=q) |
            Q(host__icontains=q) |
            Q(subdomain__icontains=q) |
            Q(user_agent__icontains=q) |
            Q(referer__icontains=q)
        )

    # 类型筛选
    if log_type == "spider":
        qs = qs.filter(is_spider=True)
    elif log_type == "engine":
        qs = qs.filter(is_from_search_engine=True, is_spider=False)
    elif log_type == "normal":
        qs = qs.filter(is_spider=False, is_from_search_engine=False)

    # 状态码筛选
    if status_code:
        try:
            code = int(status_code)
            qs = qs.filter(status_code=code)
        except ValueError:
            pass

    # 子域名筛选
    if subdomain:
        qs = qs.filter(subdomain__iexact=subdomain)

    # 日期范围筛选
    if date_from:
        try:
            qs = qs.filter(timestamp__gte=datetime.combine(
                datetime.strptime(date_from, "%Y-%m-%d").date(),
                datetime.min.time(),
            ))
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(timestamp__lte=datetime.combine(
                datetime.strptime(date_to, "%Y-%m-%d").date(),
                datetime.max.time(),
            ))
        except ValueError:
            pass

    # ---- 统计信息（在筛选后的结果上计算） ----
    total = qs.count()
    spider_count = qs.filter(is_spider=True).count()
    engine_count = qs.filter(is_from_search_engine=True, is_spider=False).count()
    normal_count = total - spider_count - engine_count
    redirect_count = qs.filter(status_code=302).count()

    # 所有出现过的子域名列表（供下拉筛选用 - 仅从当前筛选集取）
    subdomain_list = (
        qs.filter(subdomain__gt="")
        .values_list("subdomain", flat=True)
        .distinct()[:50]  # 限制数量，避免下拉太大
    )

    # ---- 分页 ----
    paginator = Paginator(qs.only(
        "id", "timestamp", "ip", "method", "path", "host",
        "subdomain", "is_spider", "is_from_search_engine",
        "status_code",
    ), page_size)

    try:
        page_obj = paginator.page(page)
    except Exception:
        page_obj = paginator.page(1)

    page_range = _build_page_range(paginator.num_pages, page_obj.number)

    context = {
        # 分页数据
        "logs": page_obj,
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "page_range": page_range,
        "has_prev": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "prev_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
        # 统计
        "total": total,
        "spider_count": spider_count,
        "engine_count": engine_count,
        "normal_count": normal_count,
        "redirect_count": redirect_count,
        # 当前筛选条件（回填到表单）
        "current_q": q,
        "current_type": log_type,
        "current_status": status_code,
        "current_subdomain": subdomain,
        "current_date_from": date_from,
        "current_date_to": date_to,
        "current_page_size": page_size,
        # 子域名下拉列表
        "subdomain_list": subdomain_list,
    }
    return render(request, "stats.html", context)


def stats_detail(request, log_id):
    """AJAX 接口：返回单条日志的完整信息（JSON）。"""
    try:
        log = RequestLog.objects.get(id=log_id)
    except RequestLog.DoesNotExist:
        return JsonResponse({"error": "记录不存在"}, status=404)

    data = {
        "id": log.id,
        "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "ip": log.ip,
        "method": log.method,
        "path": log.path,
        "full_path": log.full_path,
        "user_agent": log.user_agent,
        "referer": log.referer,
        "accept_language": log.accept_language,
        "accept_encoding": log.accept_encoding,
        "host": log.host,
        "subdomain": log.subdomain,
        "is_spider": log.is_spider,
        "matched_spider": log.matched_spider,
        "is_from_search_engine": log.is_from_search_engine,
        "matched_engine": log.matched_engine,
        "status_code": log.status_code,
        "response_template": log.response_template,
    }
    return JsonResponse(data)


# ---- helpers ----------------------------------------------------------------

def _parse_page_size(raw: str) -> int:
    try:
        n = int(raw)
        return min(max(n, 10), 200)  # 10 ~ 200
    except (ValueError, TypeError):
        return 50


def _build_page_range(num_pages, current):
    """生成分页页码列表，处理省略号显示。"""
    if num_pages <= 10:
        return list(range(1, num_pages + 1))

    pages = []
    if current > 3:
        pages.extend([1, "..."])
        pages.extend(range(current - 2, current + 1))
    else:
        pages.extend(range(1, current + 1))

    if current < num_pages - 2:
        pages.extend(range(current + 1, current + 3))
        if current + 2 < num_pages - 1:
            pages.append("...")
        pages.append(num_pages)
    else:
        pages.extend(range(current + 1, num_pages + 1))

    return pages
