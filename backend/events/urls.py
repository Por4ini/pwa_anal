from django.urls import path

from . import views


urlpatterns = [
    path("v2/pwa/activity/collect", views.collect_events, name="collect_pwa_activity"),
    path("v2/pwa/activity/collect/", views.collect_events),
    path("v1/events", views.collect_events, name="collect_events"),
    path("v1/events/", views.collect_events),
    path("v2/pwa/analytics/events", views.collect_events, name="collect_pwa_events"),
    path("v2/pwa/analytics/events/", views.collect_events),
    path("dashboard/meta", views.dashboard_meta, name="dashboard_meta"),
    path("dashboard/overview", views.dashboard_overview, name="dashboard_overview"),
    path("dashboard/events", views.dashboard_events, name="dashboard_events"),
    path("dashboard/events.csv", views.dashboard_events_csv, name="dashboard_events_csv"),
]
