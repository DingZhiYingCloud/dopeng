from django.urls import path

from XingXingWeb.views.request import index
from XingXingWeb.views.stats import stats, stats_detail, stats_chart_data, stats_dashboard

urlpatterns = [
    path("", index, name="index"),
    path("stats/", stats, name="stats"),
    path("stats/detail/<int:log_id>/", stats_detail, name="stats_detail"),
    path("stats/chart-data/", stats_chart_data, name="stats_chart_data"),
    path("stats/dashboard/", stats_dashboard, name="stats_dashboard"),
]
