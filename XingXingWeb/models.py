from django.db import models


class RequestLog(models.Model):
    """
    请求访问日志，记录每次请求的详细信息。
    """
    # ---- 基础信息 ----
    timestamp = models.DateTimeField("请求时间", auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField("客户端IP", blank=True, null=True, default="", db_index=True)
    method = models.CharField("请求方法", max_length=10, blank=True, default="")
    path = models.CharField("请求路径", max_length=1024, blank=True, default="", db_index=True)
    full_path = models.TextField("完整路径(含参数)", blank=True, default="")

    # ---- 请求头 ----
    user_agent = models.TextField("User-Agent", blank=True, default="")
    referer = models.TextField("Referer", blank=True, default="")
    accept_language = models.CharField("Accept-Language", max_length=255, blank=True, default="")
    accept_encoding = models.CharField("Accept-Encoding", max_length=255, blank=True, default="")

    # ---- 主机/域名 ----
    host = models.CharField("Host", max_length=255, blank=True, default="", db_index=True)
    subdomain = models.CharField("二级域名前缀", max_length=255, blank=True, default="", db_index=True)

    # ---- 检测结果 ----
    is_spider = models.BooleanField("是否爬虫", default=False, db_index=True)
    matched_spider = models.CharField("匹配的爬虫特征", max_length=128, blank=True, default="")
    is_from_search_engine = models.BooleanField("是否来自搜索引擎", default=False, db_index=True)
    matched_engine = models.CharField("匹配的搜索引擎特征", max_length=128, blank=True, default="")

    # ---- 响应结果 ----
    status_code = models.IntegerField("响应状态码", null=True, blank=True, db_index=True)
    response_template = models.CharField("响应模板", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "请求日志"
        verbose_name_plural = "请求日志"
        ordering = ["-timestamp"]
        indexes = [
            # 复合索引：类型 + 时间，覆盖最常见的筛选排序场景
            models.Index(fields=["is_spider", "is_from_search_engine", "-timestamp"],
                         name="idx_type_time"),
            # IP + 时间，用于按IP查询
            models.Index(fields=["ip", "-timestamp"],
                         name="idx_ip_time"),
            # 子域名 + 时间
            models.Index(fields=["subdomain", "-timestamp"],
                         name="idx_subdomain_time"),
        ]

    def __str__(self):
        return f"[{self.timestamp:%m-%d %H:%M:%S}] {self.method} {self.path} ({self.ip})"
