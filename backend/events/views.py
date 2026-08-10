import csv
import hashlib
import io
import json
import re
import secrets
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDay, TruncHour, TruncWeek
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import AnalyticsEvent


EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
MAX_BODY_BYTES = 256 * 1024
MAX_BATCH_SIZE = 50
MAX_PROPERTIES_DEPTH = 6
MAX_PROPERTY_ITEMS = 100
SENSITIVE_KEY_PARTS = {
    "address",
    "authorization",
    "comment",
    "email",
    "password",
    "phone",
    "secret",
    "token",
}
ALLOWED_COMMENT_KEYS = {"order_comment", "booking_comment"}
FILTER_FIELDS = (
    "client_alias",
    "source",
    "event_name",
    "location_id",
    "location_uniq_id",
    "visitor_id",
    "session_id",
    "customer_id",
    "device_type",
    "interaction_surface",
    "product_id",
    "order_id",
    "booking_id",
)


def _text(value, max_length=256):
    return str(value or "").strip()[:max_length]


def _number(value, default=Decimal("0")):
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _sanitize_properties(value, depth=0):
    if depth > MAX_PROPERTIES_DEPTH:
        return None
    if isinstance(value, dict):
        result = {}
        for key, item in list(value.items())[:MAX_PROPERTY_ITEMS]:
            normalized_key = _text(key, 128)
            comparable_key = normalized_key.lower().replace("-", "_")
            if comparable_key in ALLOWED_COMMENT_KEYS:
                result[normalized_key] = _text(item, 4096)
                continue
            if any(part in comparable_key for part in SENSITIVE_KEY_PARTS):
                continue
            result[normalized_key] = _sanitize_properties(item, depth + 1)
        return result
    if isinstance(value, list):
        return [_sanitize_properties(item, depth + 1) for item in value[:MAX_PROPERTY_ITEMS]]
    if isinstance(value, str):
        return value[:2048]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return _text(value, 2048)


def _parse_occurred_at(value):
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000, tz=datetime_timezone.utc)
        except (OverflowError, OSError, ValueError):
            return timezone.now()
    parsed = parse_datetime(_text(value, 64))
    if parsed is None:
        return timezone.now()
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, datetime_timezone.utc)
    return parsed


def _request_ip_hash(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip_address = (forwarded.split(",", 1)[0] if forwarded else request.META.get("REMOTE_ADDR", "")).strip()
    if not ip_address:
        return ""
    salt = str(settings.ANALYTICS_IP_HASH_SALT)
    return hashlib.sha256(f"{salt}:{ip_address}".encode()).hexdigest()


def _is_rate_limited(ip_hash):
    limit = max(int(settings.ANALYTICS_REQUESTS_PER_MINUTE), 0)
    if not ip_hash or not limit:
        return False
    minute = int(timezone.now().timestamp() // 60)
    key = f"analytics-rate:{ip_hash[:24]}:{minute}"
    try:
        if cache.add(key, 1, timeout=70):
            return False
        return cache.incr(key) > limit
    except Exception:
        return False


def _build_event(raw_event, request, ip_hash):
    if not isinstance(raw_event, dict):
        raise ValueError("event must be an object")
    event_name = _text(raw_event.get("event_name"), 64).lower()
    if not EVENT_NAME_RE.match(event_name):
        raise ValueError("invalid event_name")
    try:
        event_id = uuid.UUID(_text(raw_event.get("event_id"), 64))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("invalid event_id") from exc

    source = _text(raw_event.get("source"), 16).lower()
    if source not in {"web", "qr", "unknown"}:
        source = "unknown"
    properties = raw_event.get("properties")
    is_anonymous_search = event_name == "menu_searched"

    return AnalyticsEvent(
        event_id=event_id,
        event_name=event_name,
        schema_version=max(1, min(int(raw_event.get("schema_version") or 1), 32767)),
        client_alias=_text(raw_event.get("client_alias"), 128),
        source=source,
        visitor_id="" if is_anonymous_search else _text(raw_event.get("visitor_id"), 64),
        session_id="" if is_anonymous_search else _text(raw_event.get("session_id"), 64),
        customer_id="" if is_anonymous_search else _text(raw_event.get("customer_id"), 128),
        device_type=_text(raw_event.get("device_type"), 16).lower(),
        interaction_surface=_text(raw_event.get("interaction_surface"), 32).lower(),
        location_id=_text(raw_event.get("location_id"), 128),
        location_uniq_id=_text(raw_event.get("location_uniq_id"), 128),
        table_id=_text(raw_event.get("table_id"), 128),
        product_id=_text(raw_event.get("product_id"), 128),
        order_id=_text(raw_event.get("order_id"), 128),
        booking_id=_text(raw_event.get("booking_id"), 128),
        page_path="" if is_anonymous_search else _text(raw_event.get("page_path"), 1024),
        referrer_path="" if is_anonymous_search else _text(raw_event.get("referrer_path"), 1024),
        properties=_sanitize_properties(properties if isinstance(properties, dict) else {}),
        occurred_at=_parse_occurred_at(raw_event.get("occurred_at")),
        user_agent="" if is_anonymous_search else _text(request.META.get("HTTP_USER_AGENT"), 512),
        ip_hash="" if is_anonymous_search else ip_hash,
    )


def _dashboard_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        expected = _text(settings.DASHBOARD_TOKEN, 512)
        if expected:
            supplied = _text(request.headers.get("X-Analytics-Token"), 512)
            authorization = _text(request.headers.get("Authorization"), 1024)
            if not supplied and authorization.lower().startswith("bearer "):
                supplied = authorization[7:].strip()
            if not supplied or not secrets.compare_digest(supplied, expected):
                return JsonResponse({"status": "error", "message": "unauthorized"}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def _filter_datetime(value, end=False):
    if not value:
        return None, False
    raw_value = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_value):
        parsed_date = parse_date(raw_value)
        if not parsed_date:
            return None, False
        resolved = datetime.combine(parsed_date, time.min, tzinfo=datetime_timezone.utc)
        return (resolved + timedelta(days=1), True) if end else (resolved, False)
    parsed = parse_datetime(raw_value)
    if parsed:
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, datetime_timezone.utc)
        return parsed, False
    parsed_date = parse_date(raw_value)
    if not parsed_date:
        return None, False
    resolved = datetime.combine(parsed_date, time.min, tzinfo=datetime_timezone.utc)
    return (resolved + timedelta(days=1), True) if end else (resolved, False)


def _filtered_events(request):
    queryset = AnalyticsEvent.objects.all()
    date_from, _ = _filter_datetime(request.GET.get("date_from"))
    date_to, date_to_exclusive = _filter_datetime(request.GET.get("date_to"), end=True)
    if date_from:
        queryset = queryset.filter(occurred_at__gte=date_from)
    if date_to:
        lookup = "occurred_at__lt" if date_to_exclusive else "occurred_at__lte"
        queryset = queryset.filter(**{lookup: date_to})
    for field in FILTER_FIELDS:
        value = _text(request.GET.get(field), 256)
        if value:
            queryset = queryset.filter(**{field: value})
    search = _text(request.GET.get("search"), 256)
    if search:
        queryset = queryset.filter(
            Q(event_id__icontains=search)
            | Q(client_alias__icontains=search)
            | Q(visitor_id__icontains=search)
            | Q(session_id__icontains=search)
            | Q(customer_id__icontains=search)
            | Q(location_id__icontains=search)
            | Q(location_uniq_id__icontains=search)
            | Q(product_id__icontains=search)
            | Q(order_id__icontains=search)
            | Q(booking_id__icontains=search)
            | Q(page_path__icontains=search)
        )
    return queryset


def _event_dict(event):
    return {
        "id": event.id,
        "event_id": str(event.event_id),
        "event_name": event.event_name,
        "client_alias": event.client_alias,
        "source": event.source,
        "visitor_id": event.visitor_id,
        "session_id": event.session_id,
        "customer_id": event.customer_id,
        "device_type": event.device_type,
        "interaction_surface": event.interaction_surface,
        "location_id": event.location_id,
        "location_uniq_id": event.location_uniq_id,
        "table_id": event.table_id,
        "product_id": event.product_id,
        "order_id": event.order_id,
        "booking_id": event.booking_id,
        "page_path": event.page_path,
        "referrer_path": event.referrer_path,
        "properties": event.properties,
        "occurred_at": event.occurred_at.isoformat(),
        "received_at": event.received_at.isoformat(),
        "user_agent": event.user_agent,
    }


def _breakdown(queryset, field, limit=12):
    rows = queryset.values(field).annotate(count=Count("id")).order_by("-count")[:limit]
    return [{"label": row[field] or "—", "count": row["count"]} for row in rows]


def _top_products(queryset, limit=10):
    rows = (
        queryset.exclude(product_id="")
        .values("product_id")
        .annotate(count=Count("id"), last_seen=Max("occurred_at"))
        .order_by("-count")[:limit]
    )
    names = {}
    for event in queryset.exclude(product_id="").only("product_id", "properties").order_by("-occurred_at")[:2000]:
        names.setdefault(event.product_id, _text((event.properties or {}).get("product_name"), 512))
    return [
        {
            "product_id": row["product_id"],
            "product_name": names.get(row["product_id"]) or row["product_id"],
            "count": row["count"],
            "last_seen": row["last_seen"].isoformat(),
        }
        for row in rows
    ]


def _upsell_summary(queryset):
    event_counts = dict(
        queryset.filter(event_name__in=[
            "upsell_block_impression",
            "upsell_product_impression",
            "upsell_product_clicked",
            "upsell_cart_added",
            "upsell_order_attributed",
        ])
        .values_list("event_name")
        .annotate(total=Count("id"))
    )
    quantity = Decimal("0")
    revenue = Decimal("0")
    product_totals = defaultdict(lambda: {"product_id": "", "product_name": "", "quantity": Decimal("0"), "revenue": Decimal("0")})
    attributed_events = queryset.filter(event_name="upsell_order_attributed").only("properties").iterator(chunk_size=1000)
    for event in attributed_events:
        properties = event.properties or {}
        quantity += _number(properties.get("quantity"))
        revenue += _number(properties.get("revenue"))
        for product in properties.get("products") or []:
            if not isinstance(product, dict):
                continue
            key = _text(product.get("product_id") or product.get("product_uniq_id"), 128)
            if not key:
                continue
            item = product_totals[key]
            item["product_id"] = key
            item["product_name"] = _text(product.get("product_name"), 512) or key
            item["quantity"] += _number(product.get("quantity"))
            item["revenue"] += _number(product.get("revenue"))
    products = sorted(product_totals.values(), key=lambda item: item["revenue"], reverse=True)[:10]
    clicks = event_counts.get("upsell_product_clicked", 0)
    cart_adds = event_counts.get("upsell_cart_added", 0)
    total_orders = queryset.filter(event_name="order_created").exclude(order_id="").values("order_id").distinct().count()
    attributed_orders = queryset.filter(event_name="upsell_order_attributed").exclude(order_id="").values("order_id").distinct().count()
    return {
        "block_impressions": event_counts.get("upsell_block_impression", 0),
        "product_impressions": event_counts.get("upsell_product_impression", 0),
        "clicks": clicks,
        "cart_adds": cart_adds,
        "attributed_orders": attributed_orders,
        "total_orders": total_orders,
        "order_share_rate": round(attributed_orders / total_orders * 100, 2) if total_orders else 0,
        "quantity": float(quantity),
        "revenue": float(revenue),
        "click_to_cart_rate": round(cart_adds / clicks * 100, 2) if clicks else 0,
        "click_to_order_rate": round(attributed_orders / clicks * 100, 2) if clicks else 0,
        "products": [
            {**item, "quantity": float(item["quantity"]), "revenue": float(item["revenue"])}
            for item in products
        ],
    }


def _mobile_tile_summary(queryset):
    mobile_visitors = (
        queryset.filter(device_type="mobile")
        .exclude(visitor_id="")
        .values("visitor_id")
        .distinct()
        .count()
    )
    tile_adds = queryset.filter(
        event_name="cart_item_added",
        device_type="mobile",
        interaction_surface="tile",
    )
    tile_cart_visitors = tile_adds.exclude(visitor_id="").values("visitor_id").distinct().count()
    return {
        "mobile_visitors": mobile_visitors,
        "tile_cart_visitors": tile_cart_visitors,
        "tile_cart_adds": tile_adds.count(),
        "conversion_rate": round(tile_cart_visitors / mobile_visitors * 100, 2) if mobile_visitors else 0,
    }


def _search_summary(queryset, limit=50):
    totals = defaultdict(lambda: {"query": "", "count": 0})
    total_searches = 0
    for event in queryset.filter(event_name="menu_searched").only("properties").iterator(chunk_size=1000):
        query = _text((event.properties or {}).get("search_term"), 256)
        if not query:
            continue
        key = query.casefold()
        totals[key]["query"] = totals[key]["query"] or query
        totals[key]["count"] += 1
        total_searches += 1
    queries = sorted(totals.values(), key=lambda item: (-item["count"], item["query"].casefold()))[:limit]
    return {"total": total_searches, "unique": len(totals), "queries": queries}


def _comment_feed(queryset, event_name, property_name, id_field, limit=100):
    comments = []
    total = 0
    events = queryset.filter(event_name=event_name).only(
        "occurred_at", "client_alias", "source", "location_id", "location_uniq_id",
        id_field, "properties",
    ).order_by("-occurred_at").iterator(chunk_size=1000)
    for event in events:
        comment = _text((event.properties or {}).get(property_name), 4096)
        if not comment:
            continue
        total += 1
        if len(comments) >= limit:
            continue
        comments.append({
            "occurred_at": event.occurred_at.isoformat(),
            "client_alias": event.client_alias,
            "source": event.source,
            "location": event.location_uniq_id or event.location_id,
            "reference_id": getattr(event, id_field) or _text((event.properties or {}).get(id_field), 128),
            "comment": comment,
        })
    return {"total": total, "items": comments}


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok", "database": "ok"})
    except Exception:
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)


@csrf_exempt
@require_POST
def collect_events(request):
    if len(request.body) > MAX_BODY_BYTES:
        return JsonResponse({"status": "error", "message": "payload_too_large"}, status=413)
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"status": "error", "message": "invalid_json"}, status=400)
    raw_events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(raw_events, list) or not raw_events:
        return JsonResponse({"status": "error", "message": "events_required"}, status=400)
    if len(raw_events) > MAX_BATCH_SIZE:
        return JsonResponse({"status": "error", "message": "batch_too_large"}, status=413)

    ip_hash = _request_ip_hash(request)
    if _is_rate_limited(ip_hash):
        return JsonResponse({"status": "error", "message": "rate_limited"}, status=429)

    events = []
    errors = []
    seen_ids = set()
    duplicates = 0
    for index, raw_event in enumerate(raw_events):
        try:
            event = _build_event(raw_event, request, ip_hash)
            if event.event_id in seen_ids:
                duplicates += 1
                continue
            seen_ids.add(event.event_id)
            events.append(event)
        except (TypeError, ValueError) as exc:
            errors.append({"index": index, "message": str(exc)})
    if not events:
        return JsonResponse({"status": "error", "message": "no_valid_events", "errors": errors}, status=400)

    existing_ids = set(
        AnalyticsEvent.objects.filter(event_id__in=[event.event_id for event in events]).values_list("event_id", flat=True)
    )
    new_events = [event for event in events if event.event_id not in existing_ids]
    duplicates += len(events) - len(new_events)
    AnalyticsEvent.objects.bulk_create(new_events, ignore_conflicts=True, batch_size=500)
    return JsonResponse(
        {"status": "accepted", "accepted": len(new_events), "duplicates": duplicates, "rejected": len(errors), "errors": errors},
        status=202,
    )


@require_GET
@_dashboard_required
def dashboard_meta(request):
    def options(field, limit=500):
        return list(
            AnalyticsEvent.objects.exclude(**{field: ""})
            .values_list(field, flat=True)
            .distinct()
            .order_by(field)[:limit]
        )

    bounds = AnalyticsEvent.objects.aggregate(first=Max("occurred_at"), last=Max("received_at"))
    return JsonResponse({
        "filters": {
            "client_aliases": options("client_alias"),
            "sources": options("source"),
            "event_names": options("event_name"),
            "locations": options("location_id"),
            "location_uniq_ids": options("location_uniq_id"),
            "device_types": options("device_type"),
            "interaction_surfaces": options("interaction_surface"),
        },
        "latest_event_at": bounds["first"].isoformat() if bounds["first"] else None,
        "dashboard_token_required": bool(settings.DASHBOARD_TOKEN),
        "retention_days": settings.ANALYTICS_RETENTION_DAYS,
    })


@require_GET
@_dashboard_required
def dashboard_overview(request):
    queryset = _filtered_events(request)
    totals = queryset.aggregate(
        total_events=Count("id"),
        visitors=Count("visitor_id", distinct=True, filter=~Q(visitor_id="")),
        sessions=Count("session_id", distinct=True, filter=~Q(session_id="")),
        customers=Count("customer_id", distinct=True, filter=~Q(customer_id="")),
        orders=Count("order_id", distinct=True, filter=Q(event_name="order_created") & ~Q(order_id="")),
    )
    funnel_names = ["session_started", "product_viewed", "cart_item_added", "checkout_started", "order_created", "purchase_completed"]
    funnel_counts = {
        row["event_name"]: row["count"]
        for row in queryset.filter(event_name__in=funnel_names).values("event_name").annotate(count=Count("id"))
    }

    first_event = queryset.order_by("occurred_at").values_list("occurred_at", flat=True).first()
    last_event = queryset.order_by("-occurred_at").values_list("occurred_at", flat=True).first()
    span = (last_event - first_event) if first_event and last_event else timedelta(0)
    if span <= timedelta(days=2):
        bucket_function, granularity = TruncHour, "hour"
    elif span <= timedelta(days=120):
        bucket_function, granularity = TruncDay, "day"
    else:
        bucket_function, granularity = TruncWeek, "week"
    timeline = list(
        queryset.annotate(bucket=bucket_function("occurred_at"))
        .values("bucket")
        .annotate(events=Count("id"), visitors=Count("visitor_id", distinct=True, filter=~Q(visitor_id="")))
        .order_by("bucket")
    )

    top_pages = [
        {"page_path": row["page_path"], "count": row["count"]}
        for row in queryset.exclude(page_path="").values("page_path").annotate(count=Count("id")).order_by("-count")[:10]
    ]
    order_total = Decimal("0")
    for event in queryset.filter(event_name="order_created").only("properties").iterator(chunk_size=1000):
        order_total += _number((event.properties or {}).get("total"))

    return JsonResponse({
        "totals": {**totals, "order_revenue": float(order_total)},
        "funnel": [{"event_name": name, "count": funnel_counts.get(name, 0)} for name in funnel_names],
        "timeline": [
            {"bucket": row["bucket"].isoformat(), "events": row["events"], "visitors": row["visitors"]}
            for row in timeline
        ],
        "granularity": granularity,
        "breakdowns": {
            "events": _breakdown(queryset, "event_name", 15),
            "clients": _breakdown(queryset.exclude(client_alias=""), "client_alias"),
            "sources": _breakdown(queryset, "source"),
            "locations": _breakdown(queryset.exclude(location_id=""), "location_id"),
        },
        "top_products": _top_products(queryset),
        "top_pages": top_pages,
        "upsell": _upsell_summary(queryset),
        "mobile_tile": _mobile_tile_summary(queryset),
        "searches": _search_summary(queryset),
        "order_comments": _comment_feed(queryset, "order_created", "order_comment", "order_id"),
        "booking_comments": _comment_feed(queryset, "booking_created", "booking_comment", "booking_id"),
        "range": {
            "first": first_event.isoformat() if first_event else None,
            "last": last_event.isoformat() if last_event else None,
        },
    })


@require_GET
@_dashboard_required
def dashboard_events(request):
    queryset = _filtered_events(request)
    try:
        page = max(int(request.GET.get("page", 1)), 1)
        page_size = min(max(int(request.GET.get("page_size", 50)), 10), 200)
    except (TypeError, ValueError):
        page, page_size = 1, 50
    total = queryset.count()
    offset = (page - 1) * page_size
    events = [_event_dict(event) for event in queryset[offset:offset + page_size]]
    return JsonResponse({"count": total, "page": page, "page_size": page_size, "results": events})


class _Echo:
    def write(self, value):
        return value


@require_GET
@_dashboard_required
def dashboard_events_csv(request):
    queryset = _filtered_events(request).iterator(chunk_size=1000)
    fields = [
        "event_id", "event_name", "occurred_at", "client_alias", "source", "visitor_id", "session_id",
        "customer_id", "device_type", "interaction_surface", "location_id", "location_uniq_id", "table_id",
        "product_id", "order_id", "booking_id", "page_path",
        "referrer_path", "properties",
    ]

    def rows():
        writer = csv.writer(_Echo())
        yield writer.writerow(fields)
        for event in queryset:
            yield writer.writerow([
                str(event.event_id), event.event_name, event.occurred_at.isoformat(), event.client_alias, event.source,
                event.visitor_id, event.session_id, event.customer_id, event.device_type, event.interaction_surface,
                event.location_id, event.location_uniq_id, event.table_id, event.product_id, event.order_id,
                event.booking_id, event.page_path, event.referrer_path,
                json.dumps(event.properties, ensure_ascii=False),
            ])

    response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="pwa-analytics-{date.today().isoformat()}.csv"'
    return response
