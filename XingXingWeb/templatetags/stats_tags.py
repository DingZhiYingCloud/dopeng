from urllib.parse import urlencode

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    替换/新增当前 URL 的查询参数，保留其他参数。
    如果参数值为 None 或空字符串，则从 URL 中移除该参数。

    用法: {% url_replace page=2 %}  →  ?q=xxx&page=2
          {% url_replace page='' %} →  ?q=xxx（移除 page）
    """
    request = context.get("request")
    if not request:
        return ""

    # 用普通 dict 避免 QueryDict 的 urlencode 行为不一致
    params = dict(request.GET.lists())
    for key, value in kwargs.items():
        if value is None or value == "":
            params.pop(key, None)
        else:
            params[key] = [str(value)]

    return urlencode(params, doseq=True)


@register.simple_tag(takes_context=True)
def url_add_param(context, **kwargs):
    """
    在现有 URL 参数基础上追加/覆盖参数。
    与 url_replace 的区别：如果值是空/None 则忽略，不移除。
    """
    request = context.get("request")
    if not request:
        return ""

    params = dict(request.GET.lists())
    for key, value in kwargs.items():
        if value is not None and value != "":
            params[key] = [str(value)]

    return urlencode(params, doseq=True)
