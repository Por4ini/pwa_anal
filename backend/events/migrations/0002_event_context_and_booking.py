from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("events", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="analyticsevent",
            name="booking_id",
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name="analyticsevent",
            name="device_type",
            field=models.CharField(blank=True, db_index=True, max_length=16),
        ),
        migrations.AddField(
            model_name="analyticsevent",
            name="interaction_surface",
            field=models.CharField(blank=True, db_index=True, max_length=32),
        ),
    ]
