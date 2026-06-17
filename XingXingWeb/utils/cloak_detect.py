"""
cloak_detect · 纯判断版
======================

把 ``beacon.min.js`` 里的"**蜘蛛 / 人类**"和"**是否来自搜索引擎**"
两类判定逻辑完整移植到 Python。

**本模块只做判断,不做任何跳转、URL 生成、外部访问等副作用。**
外部业务(Flask/Django/自建网关)拿到判定结果后,自行决定如何处置。

用法
----
方式 A · 直接用默认实例
    >>> from cloak_detect import detector
    >>> detector.is_spider("Mozilla/5.0 (compatible; bingbot/2.0)")
    True
    >>> detector.is_from_search_engine("https://www.google.com/search?q=x")
    True

方式 B · 自行实例化(可注入自定义特征 / 调试开关)
    >>> from cloak_detect import CloakDetector
    >>> d = CloakDetector(debug=True)
    >>> d.detect(ua, ref)
    DetectionResult(is_spider=False, is_from_search_engine=True, ...)

对应 JS 源
----------
``系统/系统2/beacon.min.js`` 中的 ``isSpider()`` 与 ``isFromSearchEngine()``。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

# =============================================================================
# 默认特征库(与 beacon.min.js 第 2 行 / 第 10-14 行一一对应)
# =============================================================================

# 搜索引擎 referer 特征 —— 子串匹配,全部带点(避免误报)
DEFAULT_SEARCH_ENGINES: tuple[str, ...] = (
    "google.", "bing.", "yahoo.", "yandex.", "duckduckgo.",
    "baidu.", "sogou.", "sm.", "360.",
)

# 爬虫 UA 特征 —— 子串匹配
DEFAULT_SPIDERS: tuple[str, ...] = (
    "googlebot", "bingbot", "baiduspider", "yandexbot", "duckduckbot",
    "sogou", "sosospider", "360spider", "slurp", "mj12bot", "ahrefsbot",
    "semrushbot", "seznambot", "dotbot", "crawler", "spider", "bot",
)


# =============================================================================
# 返回值
# =============================================================================

@dataclass(frozen=True)
class DetectionResult:
    """
    ``CloakDetector.detect()`` 的返回值,所有判定信息一次性给齐。

    字段
    ----
    is_spider : bool
        True = 命中爬虫 UA(对应 beacon.min.js 中"留本页"那一支)
    is_from_search_engine : bool
        True = referer 命中已知搜索引擎(对应"跳钓鱼"那一支)
    matched_spider : Optional[str]
        命中的爬虫特征(如 ``"bingbot"``),未命中则为 ``None``
    matched_engine : Optional[str]
        命中的搜索引擎特征(如 ``"bing."``),未命中则为 ``None``
    """
    is_spider: bool
    is_from_search_engine: bool
    matched_spider: Optional[str] = None
    matched_engine: Optional[str] = None

    def __bool__(self) -> bool:  # 让 `if result:` 能直接用
        return self.is_spider or self.is_from_search_engine


# =============================================================================
# 核心:判定器类
# =============================================================================

class CloakDetector:
    """
    蜘蛛 / 搜索引擎 referer 判定器(纯判断,无副作用)。

    可注入参数
    ----------
    search_engines : Sequence[str] | None
        自定义搜索引擎 referer 特征列表;为 ``None`` 时使用 ``DEFAULT_SEARCH_ENGINES``。
    spiders : Sequence[str] | None
        自定义爬虫 UA 特征列表;为 ``None`` 时使用 ``DEFAULT_SPIDERS``。
    debug : bool
        是否打印调试日志(默认 ``False``,打开后每次命中都会用 ``loguru`` 输出
        ``DEBUG`` 级日志,关闭则完全静默)。
    """

    def __init__(
        self,
        search_engines: Optional[Sequence[str]] = None,
        spiders: Optional[Sequence[str]] = None,
    ) -> None:
        # 全部转小写 + 冻结成 tuple,匹配时也把入参转小写,保证大小写不敏感
        self._search_engines: tuple[str, ...] = tuple(
            s.lower() for s in (search_engines if search_engines is not None else DEFAULT_SEARCH_ENGINES)
        )
        self._spiders: tuple[str, ...] = tuple(
            s.lower() for s in (spiders if spiders is not None else DEFAULT_SPIDERS)
        )
    # ---- 私有工具 --------------------------------------------------------

  

    # ---- 单独判断(对外暴露的两个核心方法)-------------------------------

    def is_spider(self, user_agent: str) -> bool:
        """
        判定 UA 是否为已知爬虫/蜘蛛。

        对应 ``beacon.min.js: function isSpider()``。
        大小写不敏感;空 / ``None`` 一律返回 ``False``。

        示例
        ----
        >>> d = CloakDetector()
        >>> d.is_spider("Mozilla/5.0 (compatible; Googlebot/2.1)")
        True
        >>> d.is_spider("Mozilla/5.0 Chrome/120.0")
        False
        """
        ua = (user_agent or "").lower()
        for spider in self._spiders:
            if spider in ua:
                self._log(f"✓ UA 命中爬虫: {spider} (ua={ua[:60]!r})")
                return True
        return False

    def is_from_search_engine(self, referer: str) -> bool:
        """
        判定 referer 是否来自已知搜索引擎。

        对应 ``beacon.min.js: function isFromSearchEngine()``。
        大小写不敏感;空 / ``None`` 一律返回 ``False``。

        示例
        ----
        >>> d = CloakDetector()
        >>> d.is_from_search_engine("https://www.bing.com/search?q=abc")
        True
        >>> d.is_from_search_engine("https://github.com/xxx")
        False
        """
        ref = (referer or "").lower()
        for engine in self._search_engines:
            if engine in ref:
                self._log(f"✓ referer 命中搜索引擎: {engine} (ref={ref[:60]!r})")
                return True
        return False

    # ---- 综合判断(一次性拿到全部信息)-----------------------------------

    def detect(
        self,
        user_agent: str = "",
        referer: str = "",
    ) -> DetectionResult:
        """
        一次调用,同时判定"是否爬虫"和"是否来自搜索引擎"。

        等价于 ``is_spider(ua)`` + ``is_from_search_engine(ref)``,
        但额外返回两个命中的具体特征(便于日志/审计)。

        注意:**本方法不引入优先级,只做独立判定。**
        JS 中"蜘蛛优先"的判断顺序由调用方决定(见下方代码注释)。

        示例
        ----
        >>> d = CloakDetector(debug=True)
        >>> d.detect(
        ...     "Mozilla/5.0 Chrome/120.0",
        ...     "https://www.google.com/search?q=whatsapp",
        ... )
        DetectionResult(is_spider=False, is_from_search_engine=True,
                        matched_spider=None, matched_engine='google.')
        """
        ua = (user_agent or "").lower()
        ref = (referer or "").lower()

        matched_spider: Optional[str] = next(
            (s for s in self._spiders if s in ua), None
        )
        matched_engine: Optional[str] = next(
            (e for e in self._search_engines if e in ref), None
        )

        return DetectionResult(
            is_spider=matched_spider is not None,
            is_from_search_engine=matched_engine is not None,
            matched_spider=matched_spider,
            matched_engine=matched_engine,
        )

    # ---- WSGI / HTTP 框架适配 ------------------------------------------

    def detect_from_environ(self, environ: dict) -> DetectionResult:
        """
        从 WSGI ``environ`` 字典自动提取 ``HTTP_USER_AGENT`` 和
        ``HTTP_REFERER``,然后调用 :meth:`detect`。

        兼容 Flask / Django / Bottle / FastAPI(ASGI 可手动转 dict)。

        示例(Flask)
        ------------
        >>> from flask import request
        >>> d = CloakDetector()
        >>> result = d.detect_from_environ(request.environ)
        """
        ua = environ.get("HTTP_USER_AGENT", "") or ""
        ref = environ.get("HTTP_REFERER", "") or ""
        return self.detect(ua, ref)


# =============================================================================
# 开箱即用的默认实例
# =============================================================================
# 用 ``from cloak_detect import detector`` 即可直接调用,无需每次新建。
# 如果想自定义特征 / 打开调试,请自行 ``CloakDetector(...)``。

detector: CloakDetector = CloakDetector()


__all__ = [
    "CloakDetector",
    "DetectionResult",
    "DEFAULT_SEARCH_ENGINES",
    "DEFAULT_SPIDERS",
    "detector",
]
