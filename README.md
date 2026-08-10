# PWA Analytics

Standalone first-party analytics collector and dashboard for GetOrder web/QR storefronts.

The project contains:

- a public event ingestion API compatible with the PWA event contract;
- a protected dashboard API with filtering, aggregation and CSV export;
- a Vue dashboard for events, visitors, sessions, orders, products and OrderMore attribution;
- its own PostgreSQL database;
- nginx, Django/Gunicorn and PostgreSQL managed by one Docker Compose file.

Only the `gateway` service publishes a host port:

```text
127.0.0.1:67 -> gateway -> frontend:80
                         -> backend:8000 -> PostgreSQL
```

`frontend`, `backend` and `db` remain internal to the Compose network.

## Quick start

```bash
cp .env.example .env
# Set real secrets in .env
docker compose up -d --build
```

Open <http://127.0.0.1:67> and enter the value from `DASHBOARD_TOKEN`.

The repository contains a gitignored local `.env` with these development values:

```text
Dashboard: http://127.0.0.1:67
Token: local-dashboard-token
Collector: http://127.0.0.1:67/api/v2/pwa/analytics/events
Health: http://127.0.0.1:67/health/
```

## Connect pwa_api

Set the runtime setting for web and QR services:

```env
ANALYTICS_COLLECTOR_URL=http://127.0.0.1:67/api/v2/pwa/analytics/events
```

Production collector and dashboard host:

```env
ANALYTICS_COLLECTOR_URL=https://api.squadras.cc/api/v2/pwa/analytics/events
CORS_ALLOW_ALL_ORIGINS=true
```

`ANALYTICS_COLLECTOR_URL` is rendered into the PWA page at runtime, so changing the collector host does not require changing event integrations. A normal web/QR deployment may still regenerate static assets for unrelated changes.

## API

Public ingestion routes:

```text
POST /api/v1/events
POST /api/v2/pwa/analytics/events
```

Payload:

```json
{
  "events": [
    {
      "event_id": "11f0c9ac-98b5-4c10-b5ca-43ac61af6494",
      "event_name": "product_viewed",
      "schema_version": 1,
      "occurred_at": "2026-08-10T12:00:00Z",
      "client_alias": "demo-client",
      "source": "web",
      "visitor_id": "visitor-uuid",
      "session_id": "session-uuid",
      "location_id": "16751",
      "product_id": "42",
      "page_path": "/market/demo/product/42",
      "properties": {
        "product_name": "Sauce",
        "unit_price": 125
      }
    }
  ]
}
```

Dashboard routes require `X-Analytics-Token: <DASHBOARD_TOKEN>`:

```text
GET /api/dashboard/meta
GET /api/dashboard/overview
GET /api/dashboard/events
GET /api/dashboard/events.csv
```

Supported filters:

```text
date_from, date_to, client_alias, source, event_name, device_type,
interaction_surface,
location_id, location_uniq_id, visitor_id, session_id,
customer_id, product_id, order_id, booking_id, search
```

## Dashboard contents

- total events, unique visitors, sessions and authenticated customers;
- created orders and their recorded total;
- hourly/daily/weekly event and visitor timeline;
- session → product → cart → checkout → order → purchase funnel;
- event, client, source and location breakdowns;
- top products and pages;
- raw event journal with details and pagination;
- filtered CSV export;
- OrderMore block impressions, product impressions, clicks, cart additions,
  attributed orders, final ordered quantity, revenue and product breakdown.
- percentage of orders containing an attributed OrderMore product;
- unique mobile visitors and the share that added from tile mode;
- aggregated anonymous search terms;
- order and booking comment feeds.

OrderMore attribution counts only products that were added through the block and still existed in the final order payload. Impressions and clicks alone are not counted as ordered products.

## Privacy and reliability

- Raw IP addresses are never stored; the service stores a salted SHA-256 hash.
- Keys containing phone, email, address, token, password, authorization or secret are removed recursively from event properties.
- Only the explicit `order_comment` and `booking_comment` fields are retained;
  they may contain personal data and therefore remain behind the dashboard token.
- Search events retain the term and business context, but the collector removes
  visitor/session/customer IDs, IP hash, User-Agent, page path and referrer.
- `event_id` is unique, making browser retries idempotent.
- The request limit is configurable per IP/minute.
- A request is limited to 50 events and 256 KiB.
- The browser collector may send `text/plain` to avoid a CORS preflight; the body is still JSON.
- Dashboard data is protected by a token that is not compiled into the frontend bundle.

For production, replace every secret in `.env`, use HTTPS, and do not expose PostgreSQL outside the Compose network. The event collector accepts tenant storefront origins; dashboard reads remain protected by `DASHBOARD_TOKEN`.

## Operations

View status and logs:

```bash
docker compose ps
docker compose logs -f gateway backend frontend
```

Run backend tests:

```bash
docker compose exec backend python manage.py test
```

Delete events older than the configured retention period:

```bash
docker compose exec backend python manage.py purge_events
docker compose exec backend python manage.py purge_events --days 365
```

Create a database backup:

```bash
docker compose exec -T db pg_dump -U pwa_analytics -d pwa_analytics > pwa_analytics.sql
```

Stop the application without deleting data:

```bash
docker compose down
```

Do not use `docker compose down -v` unless the PostgreSQL data volume should be permanently deleted.
