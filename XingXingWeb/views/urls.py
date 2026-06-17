from django.urls import path

from XingXingWeb.views.request import index
from XingXingWeb.views.stats import stats, stats_detail

urlpatterns = [
    path("", index, name="index"),
    path("stats/", stats, name="stats"),
    path("stats/detail/<int:log_id>/", stats_detail, name="stats_detail"),
]
