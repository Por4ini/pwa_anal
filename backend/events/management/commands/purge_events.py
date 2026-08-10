from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import AnalyticsEvent


class Command(BaseCommand):
    help = "Delete analytics events older than the configured retention period."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=settings.ANALYTICS_RETENTION_DAYS)

    def handle(self, *args, **options):
        days = max(options["days"], 1)
        deleted, _ = AnalyticsEvent.objects.filter(occurred_at__lt=timezone.now() - timedelta(days=days)).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} events older than {days} days."))

