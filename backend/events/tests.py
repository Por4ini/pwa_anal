import json
import uuid

from django.test import TestCase, override_settings

from .models import AnalyticsEvent


@override_settings(DASHBOARD_TOKEN="dashboard-secret", ANALYTICS_REQUESTS_PER_MINUTE=0)
class AnalyticsApiTests(TestCase):
    endpoint = "/api/v2/pwa/analytics/events"

    def event(self, **overrides):
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_name": "product_viewed",
            "schema_version": 1,
            "occurred_at": "2026-08-10T12:00:00Z",
            "client_alias": "test-client",
            "source": "web",
            "visitor_id": "visitor-1",
            "session_id": "session-1",
            "customer_id": "customer-1",
            "device_type": "mobile",
            "interaction_surface": "tile",
            "location_id": "16751",
            "product_id": "42",
            "properties": {
                "product_name": "Sauce",
                "phone": "+380000000000",
                "order_comment": "Без цибулі",
            },
        }
        payload.update(overrides)
        return payload

    def post_events(self, events):
        return self.client.post(self.endpoint, data=json.dumps({"events": events}), content_type="text/plain")

    def dashboard_get(self, path, params=None):
        return self.client.get(path, params or {}, HTTP_X_ANALYTICS_TOKEN="dashboard-secret")

    def test_accepts_events_and_removes_sensitive_properties(self):
        response = self.post_events([self.event()])

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["accepted"], 1)
        stored = AnalyticsEvent.objects.get()
        self.assertEqual(stored.properties["product_name"], "Sauce")
        self.assertEqual(stored.properties["order_comment"], "Без цибулі")
        self.assertNotIn("phone", stored.properties)
        self.assertEqual(stored.device_type, "mobile")
        self.assertEqual(stored.interaction_surface, "tile")
        self.assertTrue(stored.ip_hash)

    def test_duplicate_event_is_idempotent(self):
        event = self.event()
        self.post_events([event])
        response = self.post_events([event])

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["accepted"], 0)
        self.assertEqual(response.json()["duplicates"], 1)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)

    def test_dashboard_requires_token_and_applies_filters(self):
        self.post_events([
            self.event(event_name="product_viewed", source="web"),
            self.event(event_name="cart_item_added", source="qr", event_id=str(uuid.uuid4())),
        ])

        self.assertEqual(self.client.get("/api/dashboard/overview").status_code, 401)
        response = self.dashboard_get("/api/dashboard/overview", {"source": "qr"})
        dated_response = self.dashboard_get(
            "/api/dashboard/overview",
            {"date_from": "2026-08-10", "date_to": "2026-08-10"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["totals"]["total_events"], 1)
        self.assertEqual(response.json()["breakdowns"]["events"][0]["label"], "cart_item_added")
        self.assertEqual(dated_response.json()["totals"]["total_events"], 2)

    def test_events_api_paginates_and_csv_exports(self):
        self.post_events([self.event()])

        response = self.dashboard_get("/api/dashboard/events", {"page_size": 10})
        csv_response = self.dashboard_get("/api/dashboard/events.csv")

        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["product_id"], "42")
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response["Content-Type"], "text/csv; charset=utf-8")

    def test_manager_metrics_search_privacy_and_comment_feeds(self):
        events = [
            self.event(event_name="session_started", visitor_id="mobile-1", product_id="", properties={}),
            self.event(event_name="session_started", visitor_id="mobile-2", product_id="", properties={}),
            self.event(event_name="cart_item_added", visitor_id="mobile-1", properties={"product_name": "Roll"}),
            self.event(event_name="order_created", visitor_id="mobile-1", order_id="order-1", product_id="", properties={"total": 500, "order_comment": "Без васабі"}),
            self.event(event_name="order_created", visitor_id="mobile-2", order_id="order-2", product_id="", properties={"total": 700}),
            self.event(event_name="upsell_order_attributed", visitor_id="mobile-1", order_id="order-1", product_id="", properties={"quantity": 1, "revenue": 50, "products": []}),
            self.event(event_name="menu_searched", visitor_id="must-disappear", session_id="must-disappear", customer_id="must-disappear", page_path="/private", product_id="", properties={"search_term": "Філадельфія"}),
            self.event(event_name="booking_created", visitor_id="mobile-1", booking_id="booking-1", product_id="", properties={"booking_comment": "Біля вікна", "guest_count": 2}),
        ]

        response = self.post_events(events)
        overview = self.dashboard_get("/api/dashboard/overview").json()
        search = AnalyticsEvent.objects.get(event_name="menu_searched")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(overview["upsell"]["total_orders"], 2)
        self.assertEqual(overview["upsell"]["attributed_orders"], 1)
        self.assertEqual(overview["upsell"]["order_share_rate"], 50.0)
        self.assertEqual(overview["mobile_tile"]["mobile_visitors"], 2)
        self.assertEqual(overview["mobile_tile"]["tile_cart_visitors"], 1)
        self.assertEqual(overview["mobile_tile"]["conversion_rate"], 50.0)
        self.assertEqual(overview["searches"]["queries"][0], {"query": "Філадельфія", "count": 1})
        self.assertEqual(overview["order_comments"]["items"][0]["comment"], "Без васабі")
        self.assertEqual(overview["booking_comments"]["items"][0]["comment"], "Біля вікна")
        self.assertEqual(search.visitor_id, "")
        self.assertEqual(search.session_id, "")
        self.assertEqual(search.customer_id, "")
        self.assertEqual(search.page_path, "")
        self.assertEqual(search.user_agent, "")
        self.assertEqual(search.ip_hash, "")
