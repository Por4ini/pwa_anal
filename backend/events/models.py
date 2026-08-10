from django.db import models


class AnalyticsEvent(models.Model):
    event_id = models.UUIDField(unique=True)
    event_name = models.CharField(max_length=64, db_index=True)
    schema_version = models.PositiveSmallIntegerField(default=1)

    client_alias = models.CharField(max_length=128, blank=True, db_index=True)
    source = models.CharField(max_length=16, default="unknown", db_index=True)
    visitor_id = models.CharField(max_length=64, blank=True, db_index=True)
    session_id = models.CharField(max_length=64, blank=True, db_index=True)
    customer_id = models.CharField(max_length=128, blank=True, db_index=True)
    device_type = models.CharField(max_length=16, blank=True, db_index=True)
    interaction_surface = models.CharField(max_length=32, blank=True, db_index=True)

    location_id = models.CharField(max_length=128, blank=True, db_index=True)
    location_uniq_id = models.CharField(max_length=128, blank=True, db_index=True)
    table_id = models.CharField(max_length=128, blank=True)
    product_id = models.CharField(max_length=128, blank=True, db_index=True)
    order_id = models.CharField(max_length=128, blank=True, db_index=True)
    booking_id = models.CharField(max_length=128, blank=True, db_index=True)

    page_path = models.CharField(max_length=1024, blank=True)
    referrer_path = models.CharField(max_length=1024, blank=True)
    properties = models.JSONField(default=dict, blank=True)

    occurred_at = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user_agent = models.CharField(max_length=512, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "analytics_event"
        ordering = ("-occurred_at", "-id")
        indexes = [
            models.Index(fields=("client_alias", "event_name", "occurred_at"), name="an_client_event_idx"),
            models.Index(fields=("client_alias", "location_id", "occurred_at"), name="an_client_loc_idx"),
            models.Index(fields=("order_id", "event_name"), name="an_order_event_idx"),
            models.Index(fields=("visitor_id", "occurred_at"), name="an_visitor_time_idx"),
        ]

    def __str__(self):
        return f"{self.client_alias}:{self.event_name}:{self.event_id}"
