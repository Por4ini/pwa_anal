from django.contrib import admin
from django.urls import include, path

from events.views import health


urlpatterns = [
    path("health/", health, name="health"),
    path("api/", include("events.urls")),
    path("django-admin/", admin.site.urls),
]

