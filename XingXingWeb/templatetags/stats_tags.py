from django import template
from django.utils.http import urlencode

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    替换当前 URL 中的指定查询参数，保留其他参数。
    用法: {% url_replace page=2 %}
    """
    request = context.get("request")
    if not request:
        return ""

    params = request.GET.copy()
    for key, value in kwargs.items():
        params[key] = value

    return urlencode(params)
