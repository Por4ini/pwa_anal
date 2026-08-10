import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AnalyticsEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.UUIDField(unique=True)),
                ("event_name", models.CharField(db_index=True, max_length=64)),
                ("schema_version", models.PositiveSmallIntegerField(default=1)),
                ("client_alias", models.CharField(blank=True, db_index=True, max_length=128)),
                ("source", models.CharField(db_index=True, default="unknown", max_length=16)),
                ("visitor_id", models.CharField(blank=True, db_index=True, max_length=64)),
                ("session_id", models.CharField(blank=True, db_index=True, max_length=64)),
                ("customer_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("location_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("location_uniq_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("table_id", models.CharField(blank=True, max_length=128)),
                ("product_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("order_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("page_path", models.CharField(blank=True, max_length=1024)),
                ("referrer_path", models.CharField(blank=True, max_length=1024)),
                ("properties", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(db_index=True)),
                ("received_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user_agent", models.CharField(blank=True, max_length=512)),
                ("ip_hash", models.CharField(blank=True, max_length=64)),
            ],
            options={"db_table": "analytics_event", "ordering": ("-occurred_at", "-id")},
        ),
        migrations.AddIndex(model_name="analyticsevent", index=models.Index(fields=["client_alias", "event_name", "occurred_at"], name="an_client_event_idx")),
        migrations.AddIndex(model_name="analyticsevent", index=models.Index(fields=["client_alias", "location_id", "occurred_at"], name="an_client_loc_idx")),
        migrations.AddIndex(model_name="analyticsevent", index=models.Index(fields=["order_id", "event_name"], name="an_order_event_idx")),
        migrations.AddIndex(model_name="analyticsevent", index=models.Index(fields=["visitor_id", "occurred_at"], name="an_visitor_time_idx")),
    ]

