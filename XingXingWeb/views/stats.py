from datetime import datetime, timedelta

from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db.models.functions import TruncHour
from django.http import JsonResponse
from django.shortcuts import render

from XingXingWeb.models import RequestLog


def stats(request):
    """
    访问统计页面，支持搜索、筛选、分页。
    """
    # ---- 读取筛选参数 ----
    q = request.GET.get("q", "").strip()
    log_type = request.GET.get("type", "").strip()
    status_code = request.GET.get("status", "").strip()
    subdomain = request.GET.get("subdomain", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    page = request.GET.get("page", 1)
    page_size = _parse_page_size(request.GET.get("page_size", "50"))

    # ---- 构建查询集 ----
    qs = _build_queryset(q, log_type, status_code, subdomain, date_from, date_to)

    # ---- 统计信息 ----
    total = qs.count()
    spider_count = qs.filter(is_spider=True).count()
    engine_count = qs.filter(is_from_search_engine=True, is_spider=False).count()
    normal_count = total - spider_count - engine_count
    redirect_count = qs.filter(status_code=302).count()

    subdomain_list = (
        qs.filter(subdomain__gt="")
        .values_list("subdomain", flat=True)
        .distinct()[:50]
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
        "logs": page_obj,
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "page_range": page_range,
        "has_prev": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "prev_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "next_page": page_obj.next_page_number() if page_obj.has_next() else None,

        "total": total,
        "spider_count": spider_count,
        "engine_count": engine_count,
        "normal_count": normal_count,
        "redirect_count": redirect_count,

        "current_q": q,
        "current_type": log_type,
        "current_status": status_code,
        "current_subdomain": subdomain,
        "current_date_from": date_from,
        "current_date_to": date_to,
        "current_page_size": page_size,
        "subdomain_list": subdomain_list,
    }
    return render(request, "admin/stats.html", context)


def stats_detail(request, log_id):
    """AJAX 接口：返回单条日志的完整信息（JSON）。"""
    try:
        log = RequestLog.objects.get(id=log_id)
    except RequestLog.DoesNotExist:
        return JsonResponse({"error": "记录不存在"}, status=404)

    return JsonResponse({
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
    })


def stats_chart_data(request):
    """
    AJAX 接口：返回图表所需的聚合数据（JSON）。
    """
    qs = RequestLog.objects.all()

    # ---- 1. 计数 ----
    total = qs.count()
    spider_count = qs.filter(is_spider=True).count()
    engine_count = qs.filter(is_from_search_engine=True, is_spider=False).count()
    normal_count = total - spider_count - engine_count

    # ---- 2. 状态码分布 ----
    status_codes = dict(
        qs.values("status_code")
        .annotate(cnt=Count("id"))
        .values_list("status_code", "cnt")
    )

    # ---- 3. 按小时趋势（最近 48 小时） ----
    since = datetime.now() - timedelta(hours=48)
    hourly = (
        qs.filter(timestamp__gte=since)
        .annotate(hour=TruncHour("timestamp"))
        .values("hour", "is_spider", "is_from_search_engine")
        .annotate(cnt=Count("id"))
        .order_by("hour")
    )

    hourly_trend = {}
    for row in hourly:
        hour_key = row["hour"].strftime("%m-%d %H:00")
        if hour_key not in hourly_trend:
            hourly_trend[hour_key] = {"spider": 0, "engine": 0, "normal": 0}
        if row["is_spider"]:
            hourly_trend[hour_key]["spider"] += row["cnt"]
        elif row["is_from_search_engine"]:
            hourly_trend[hour_key]["engine"] += row["cnt"]
        else:
            hourly_trend[hour_key]["normal"] += row["cnt"]

    return JsonResponse({
        "total": total,
        "spider_count": spider_count,
        "engine_count": engine_count,
        "normal_count": normal_count,
        "status_codes": _serialize_status_codes(status_codes),
        "hourly_trend": hourly_trend,
    })


def stats_dashboard(request):
    """数据大屏页面，仅展示图表。"""
    return render(request, "admin/dashboard.html")


# ===================== helpers =====================

def _build_queryset(q, log_type, status_code, subdomain, date_from, date_to):
    qs = RequestLog.objects.all()

    if q:
        qs = qs.filter(
            Q(ip__icontains=q) |
            Q(path__icontains=q) |
            Q(host__icontains=q) |
            Q(subdomain__icontains=q) |
            Q(user_agent__icontains=q) |
            Q(referer__icontains=q)
        )

    if log_type == "spider":
        qs = qs.filter(is_spider=True)
    elif log_type == "engine":
        qs = qs.filter(is_from_search_engine=True, is_spider=False)
    elif log_type == "normal":
        qs = qs.filter(is_spider=False, is_from_search_engine=False)

    if status_code:
        try:
            qs = qs.filter(status_code=int(status_code))
        except ValueError:
            pass

    if subdomain:
        qs = qs.filter(subdomain__iexact=subdomain)

    if date_from:
        try:
            qs = qs.filter(timestamp__gte=datetime.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            qs = qs.filter(timestamp__lte=datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
        except ValueError:
            pass

    return qs


def _parse_page_size(raw: str) -> int:
    try:
        return min(max(int(raw), 10), 200)
    except (ValueError, TypeError):
        return 50


def _serialize_status_codes(codes: dict) -> dict:
    """将状态码中的 None/空 转为字符串 key，方便前端显示。"""
    result = {}
    for k, v in codes.items():
        key = str(k) if k is not None else "-"
        result[key] = v
    return result


def _build_page_range(num_pages, current):
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
