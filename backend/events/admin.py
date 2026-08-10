from django.contrib import admin

from .models import AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ("event_name", "client_alias", "source", "location_id", "order_id", "occurred_at")
    list_filter = ("source", "event_name", "client_alias")
    search_fields = ("event_id", "visitor_id", "session_id", "customer_id", "location_id", "order_id", "product_id")
    readonly_fields = tuple(field.name for field in AnalyticsEvent._meta.fields)
    date_hierarchy = "occurred_at"

    def has_add_permission(self, request):
        return False

