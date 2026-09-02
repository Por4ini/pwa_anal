<template>
  <main class="app-shell">
    <section v-if="!connected" class="auth-screen">
      <div class="auth-card">
        <div class="brand-mark">PA</div>
        <span class="eyebrow">GETORDER DATA</span>
        <h1>PWA Analytics</h1>
        <p>Окремий центр подій для web та QR меню.</p>
        <form @submit.prevent="connect">
          <label for="dashboard-token">Dashboard token</label>
          <input id="dashboard-token" v-model="tokenInput" type="password" autocomplete="current-password" placeholder="Введіть токен доступу" />
          <button class="button button--primary" :disabled="loading">
            {{ loading ? "Підключення…" : "Відкрити аналітику" }}
          </button>
        </form>
        <p v-if="error" class="auth-error">{{ error }}</p>
        <small>Токен зберігається тільки в sessionStorage цього браузера.</small>
      </div>
    </section>

    <template v-else>
      <header class="topbar">
        <div class="topbar__brand">
          <div class="brand-mark brand-mark--small">PA</div>
          <div>
            <span class="eyebrow">GETORDER DATA</span>
            <h1>PWA Analytics</h1>
          </div>
        </div>
        <div class="topbar__actions">
          <span class="live-status"><i></i>Collector online</span>
          <span class="updated-at">Оновлено {{ updatedLabel }}</span>
          <button class="button button--ghost" :disabled="loading" @click="refresh">↻ Оновити</button>
          <button class="icon-button" title="Вийти" @click="logout">⇥</button>
        </div>
      </header>

      <section class="content">
        <div class="hero-row">
          <div>
            <span class="eyebrow">{{ activeSection.eyebrow }}</span>
            <h2>{{ activeSection.title }}</h2>
            <p>{{ activeSection.description }}</p>
          </div>
          <button class="button button--export" @click="downloadCsv">↓ Експорт CSV</button>
        </div>

        <section class="filters-card">
          <div class="filters-card__heading">
            <div>
              <strong>Фільтри</strong>
              <span>{{ activeFilterCount }} активних</span>
            </div>
            <button class="text-button" @click="advancedFilters = !advancedFilters">
              {{ advancedFilters ? "Сховати розширені" : "Розширені фільтри" }}
            </button>
          </div>
          <div class="filters-grid">
            <label>Дата від<input v-model="filters.date_from" type="date" /></label>
            <label>Дата до<input v-model="filters.date_to" type="date" /></label>
            <label>Клієнт
              <select v-model="filters.client_alias"><option value="">Усі клієнти</option><option v-for="item in meta.filters.client_aliases" :key="item">{{ item }}</option></select>
            </label>
            <label>Джерело
              <select v-model="filters.source"><option value="">Web + QR</option><option v-for="item in meta.filters.sources" :key="item">{{ item }}</option></select>
            </label>
            <label>Подія
              <select v-model="filters.event_name"><option value="">Усі події</option><option v-for="item in meta.filters.event_names" :key="item">{{ eventLabel(item) }}</option></select>
            </label>
            <label>Локація
              <select v-model="filters.location_id"><option value="">Усі локації</option><option v-for="item in meta.filters.locations" :key="item">{{ item }}</option></select>
            </label>
          </div>
          <div v-if="advancedFilters" class="filters-grid filters-grid--advanced">
            <label>Uniq локації<input v-model.trim="filters.location_uniq_id" list="location-uniq-options" placeholder="Наприклад, u-pavla" /></label>
            <datalist id="location-uniq-options"><option v-for="item in meta.filters.location_uniq_ids" :key="item" :value="item" /></datalist>
            <label>Visitor ID<input v-model.trim="filters.visitor_id" placeholder="UUID браузера" /></label>
            <label>Session ID<input v-model.trim="filters.session_id" placeholder="UUID сесії" /></label>
            <label>Customer ID<input v-model.trim="filters.customer_id" placeholder="ID користувача" /></label>
            <label>Product ID<input v-model.trim="filters.product_id" placeholder="ID товару" /></label>
            <label>Order ID<input v-model.trim="filters.order_id" placeholder="ID замовлення" /></label>
            <label>Booking ID<input v-model.trim="filters.booking_id" placeholder="ID бронювання" /></label>
            <label>Пристрій
              <select v-model="filters.device_type"><option value="">Усі пристрої</option><option v-for="item in meta.filters.device_types" :key="item">{{ item }}</option></select>
            </label>
            <label>Місце додавання
              <select v-model="filters.interaction_surface"><option value="">Усі місця</option><option v-for="item in meta.filters.interaction_surfaces" :key="item">{{ item }}</option></select>
            </label>
            <label class="filter-wide">Пошук<input v-model.trim="filters.search" placeholder="Сторінка, подія, клієнт або будь-який ID" @keyup.enter="applyFilters" /></label>
          </div>
          <div class="filters-card__actions">
            <button class="button button--subtle" @click="resetFilters">Скинути</button>
            <button class="button button--primary" :disabled="loading" @click="applyFilters">{{ loading ? "Завантаження…" : "Застосувати" }}</button>
          </div>
        </section>

        <div v-if="error" class="notice notice--error">{{ error }}</div>

        <nav class="dashboard-tabs" role="tablist" aria-label="Розділи аналітики">
          <button
            id="overview-tab"
            class="dashboard-tab"
            :class="{ 'is-active': activeTab === 'overview' }"
            type="button"
            role="tab"
            aria-controls="overview-panel"
            :aria-selected="activeTab === 'overview'"
            @click="activeTab = 'overview'"
          >
            Огляд
          </button>
          <button
            id="dynamics-tab"
            class="dashboard-tab"
            :class="{ 'is-active': activeTab === 'dynamics' }"
            type="button"
            role="tab"
            aria-controls="dynamics-panel"
            :aria-selected="activeTab === 'dynamics'"
            @click="activeTab = 'dynamics'"
          >
            Динаміка
          </button>
          <button
            id="clicks-tab"
            class="dashboard-tab"
            :class="{ 'is-active': activeTab === 'clicks' }"
            type="button"
            role="tab"
            aria-controls="clicks-panel"
            :aria-selected="activeTab === 'clicks'"
            @click="activeTab = 'clicks'"
          >
            Кліки до замовлення
          </button>
        </nav>

        <section
          v-if="activeTab === 'clicks'"
          id="clicks-panel"
          class="panel panel--wide click-journey-panel dashboard-tab-panel"
          role="tabpanel"
          aria-labelledby="clicks-tab"
        >
          <div class="panel__heading">
            <div><span class="eyebrow">ШЛЯХ ДО ЗАМОВЛЕННЯ</span><h3>Кліки до успішного оформлення</h3></div>
            <span class="panel__meta">{{ number(overview.click_journey.orders) }} замовлень із лічильником</span>
          </div>
          <div class="journey-summary">
            <article><small>Середнє</small><strong>{{ decimal(overview.click_journey.average) }}</strong><span>кліків</span></article>
            <article><small>Медіана</small><strong>{{ decimal(overview.click_journey.median) }}</strong><span>кліків</span></article>
            <OrderClicksChart :points="overview.click_journey.timeline" />
          </div>
        </section>

        <section
          v-else-if="activeTab === 'dynamics'"
          id="dynamics-panel"
          class="panel panel--wide dashboard-tab-panel"
          role="tabpanel"
          aria-labelledby="dynamics-tab"
        >
          <div class="panel__heading">
            <div><span class="eyebrow">ДИНАМІКА</span><h3>Події та відвідувачі</h3></div>
            <span class="panel__meta">{{ granularityLabel }}</span>
          </div>
          <TimelineChart :points="overview.timeline" />
        </section>

        <div v-else id="overview-panel" class="dashboard-tab-panel" role="tabpanel" aria-labelledby="overview-tab">
        <section class="kpi-grid">
          <KpiCard label="Усього подій" :value="number(overview.totals.total_events)" icon="↗" />
          <KpiCard label="Відвідувачі" :value="number(overview.totals.visitors)" :hint="`${number(overview.totals.sessions)} сесій`" icon="◉" />
          <KpiCard label="Користувачі" :value="number(overview.totals.customers)" hint="авторизовані" icon="◎" />
          <KpiCard label="Замовлення" :value="number(overview.totals.orders)" :hint="`сума ${decimal(overview.totals.order_revenue)}`" icon="✓" tone="accent" />
        </section>

        <section class="manager-grid">
          <article class="manager-card manager-card--order-more">
            <span class="eyebrow eyebrow--light">ПОКАЗНИК МЕНЕДЖЕРА</span>
            <h3>Замовлення з «Додати ще»</h3>
            <strong>{{ decimal(overview.upsell.order_share_rate) }}%</strong>
            <p>{{ number(overview.upsell.attributed_orders) }} із {{ number(overview.upsell.total_orders) }} замовлень містять товар із блоку.</p>
          </article>
          <article class="manager-card manager-card--tile">
            <span class="eyebrow">МОБІЛЬНА ПЛИТКА</span>
            <h3>Сесії з перемиканням вигляду</h3>
            <strong>{{ number(overview.mobile_tile.switched_layout_sessions) }}</strong>
            <p>{{ decimal(overview.mobile_tile.switch_rate) }}% із {{ number(overview.mobile_tile.eligible_sessions) }} сесій меню; {{ decimal(overview.mobile_tile.return_rate) }}% тих, хто вмикав плитку, повернулися до списку.</p>
          </article>
        </section>

        <section class="panel panel--wide">
          <div class="panel__heading">
            <div><span class="eyebrow">МОБІЛЬНЕ МЕНЮ</span><h3>Чи продовжують замовлення з плитки</h3></div>
            <span class="panel__meta">{{ number(overview.mobile_tile.switch_clicks) }} перемикань</span>
          </div>
          <div class="metric-strip">
            <article><small>Перемикали вигляд</small><strong>{{ number(overview.mobile_tile.switched_layout_sessions) }}</strong><span>{{ decimal(overview.mobile_tile.switch_rate) }}% сесій</span></article>
            <article><small>Повернулися в список</small><strong>{{ number(overview.mobile_tile.returned_to_list_sessions) }}</strong><span>{{ decimal(overview.mobile_tile.return_rate) }}% після плитки</span></article>
            <article><small>Додавали з плитки</small><strong>{{ number(overview.mobile_tile.tile_cart_sessions) }}</strong><span>{{ number(overview.mobile_tile.tile_cart_adds) }} додавань</span></article>
            <article><small>Замовлення з плитки</small><strong>{{ number(overview.mobile_tile.tile_orders) }}</strong><span>{{ decimal(overview.mobile_tile.tile_order_share_rate) }}% mobile orders</span></article>
            <article><small>Tile → кошик</small><strong>{{ decimal(overview.mobile_tile.tile_cart_conversion_rate) }}%</strong><span>серед тих, хто перемкнув</span></article>
            <article><small>Tile → замовлення</small><strong>{{ decimal(overview.mobile_tile.tile_order_conversion_rate) }}%</strong><span>серед тих, хто перемкнув</span></article>
          </div>
        </section>

        <section class="panel panel--wide">
          <div class="panel__heading">
            <div><span class="eyebrow">КОНВЕРСІЯ</span><h3>Основна воронка</h3></div>
            <span class="panel__meta">за кількістю подій</span>
          </div>
          <div class="funnel">
            <template v-for="(step, index) in overview.funnel" :key="step.event_name">
              <article class="funnel__step">
                <span>{{ index + 1 }}</span>
                <p>{{ eventLabel(step.event_name) }}</p>
                <strong>{{ number(step.count) }}</strong>
                <small>{{ funnelRate(index) }}% від першого кроку</small>
              </article>
              <div v-if="index < overview.funnel.length - 1" class="funnel__arrow">→</div>
            </template>
          </div>
        </section>

        <section class="upsell-panel">
          <div class="upsell-panel__intro">
            <span class="eyebrow eyebrow--light">ORDER MORE</span>
            <h3>«Додати ще» в замовленнях</h3>
            <p>Тут рахуємо тільки товари, що були додані з блоку та реально залишились у фінальному замовленні.</p>
            <div class="upsell-rates">
              <span>Клік → кошик <strong>{{ decimal(overview.upsell.click_to_cart_rate) }}%</strong></span>
              <span>Клік → замовлення <strong>{{ decimal(overview.upsell.click_to_order_rate) }}%</strong></span>
            </div>
          </div>
          <div class="upsell-stats">
            <article><small>Покази блоку</small><strong>{{ number(overview.upsell.block_impressions) }}</strong></article>
            <article><small>Кліки</small><strong>{{ number(overview.upsell.clicks) }}</strong></article>
            <article><small>Додано в кошик</small><strong>{{ number(overview.upsell.cart_adds) }}</strong></article>
            <article><small>Замовлень</small><strong>{{ number(overview.upsell.attributed_orders) }}</strong></article>
            <article class="upsell-stats__highlight"><small>Товарів у замовленнях</small><strong>{{ decimal(overview.upsell.quantity) }}</strong></article>
            <article class="upsell-stats__highlight"><small>Виручка OrderMore</small><strong>{{ decimal(overview.upsell.revenue) }}</strong></article>
          </div>
        </section>

        <section v-if="overview.upsell.products.length" class="panel panel--wide">
          <div class="panel__heading"><div><span class="eyebrow">ORDER MORE</span><h3>Товари, що дійшли до замовлення</h3></div></div>
          <div class="table-scroll">
            <table>
              <thead><tr><th>Товар</th><th>Product ID</th><th>Кількість</th><th>Виручка</th></tr></thead>
              <tbody><tr v-for="product in overview.upsell.products" :key="product.product_id"><td><strong>{{ product.product_name }}</strong></td><td class="mono">{{ product.product_id }}</td><td>{{ decimal(product.quantity) }}</td><td>{{ decimal(product.revenue) }}</td></tr></tbody>
            </table>
          </div>
        </section>

        <section class="dashboard-grid insight-grid">
          <article class="panel">
            <div class="panel__heading">
              <div><span class="eyebrow">АНОНІМНИЙ ПОШУК</span><h3>Пошукові запити</h3></div>
              <span class="panel__meta">{{ number(overview.searches.total) }} пошуків · {{ number(overview.searches.unique) }} унікальних</span>
            </div>
            <div v-if="overview.searches.queries.length" class="table-scroll">
              <table><thead><tr><th>Запит</th><th>Кількість</th></tr></thead><tbody><tr v-for="item in overview.searches.queries" :key="item.query"><td><strong>{{ item.query }}</strong></td><td>{{ number(item.count) }}</td></tr></tbody></table>
            </div>
            <div v-else class="empty-compact">Пошукових запитів ще немає</div>
          </article>
          <article class="panel comments-panel">
            <div class="panel__heading">
              <div><span class="eyebrow">ЗАМОВЛЕННЯ</span><h3>Коментарі до замовлень</h3></div>
              <span class="panel__meta">{{ number(overview.order_comments.total) }}</span>
            </div>
            <div v-if="overview.order_comments.items.length" class="comment-feed">
              <article v-for="item in overview.order_comments.items" :key="`${item.reference_id}-${item.occurred_at}`"><p>{{ item.comment }}</p><small>{{ item.client_alias || '—' }} · {{ item.location || '—' }} · {{ item.reference_id || '—' }} · {{ dateTime(item.occurred_at) }}</small></article>
            </div>
            <div v-else class="empty-compact">Коментарів до замовлень ще немає</div>
          </article>
        </section>

        <section class="panel panel--wide comments-panel">
          <div class="panel__heading">
            <div><span class="eyebrow">БРОНЮВАННЯ</span><h3>Коментарі до бронювань</h3></div>
            <span class="panel__meta">{{ number(overview.booking_comments.total) }}</span>
          </div>
          <div v-if="overview.booking_comments.items.length" class="comment-feed comment-feed--columns">
            <article v-for="item in overview.booking_comments.items" :key="`${item.reference_id}-${item.occurred_at}`"><p>{{ item.comment }}</p><small>{{ item.client_alias || '—' }} · {{ item.location || '—' }} · {{ item.reference_id || '—' }} · {{ dateTime(item.occurred_at) }}</small></article>
          </div>
          <div v-else class="empty-compact">Коментарів до бронювань ще немає</div>
        </section>

        <section class="dashboard-grid">
          <article class="panel"><div class="panel__heading"><div><span class="eyebrow">ПОДІЇ</span><h3>Найчастіші дії</h3></div></div><BreakdownBars :items="overview.breakdowns.events" /></article>
          <article class="panel"><div class="panel__heading"><div><span class="eyebrow">КЛІЄНТИ</span><h3>Активність клієнтів</h3></div></div><BreakdownBars :items="overview.breakdowns.clients" /></article>
          <article class="panel"><div class="panel__heading"><div><span class="eyebrow">ДЖЕРЕЛО</span><h3>Web проти QR</h3></div></div><BreakdownBars :items="overview.breakdowns.sources" /></article>
          <article class="panel"><div class="panel__heading"><div><span class="eyebrow">ЛОКАЦІЇ</span><h3>Найактивніші локації</h3></div></div><BreakdownBars :items="overview.breakdowns.locations" /></article>
        </section>

        <section class="dashboard-grid">
          <article class="panel">
            <div class="panel__heading"><div><span class="eyebrow">ТОВАРИ</span><h3>Популярні товари</h3></div></div>
            <ol v-if="overview.top_products.length" class="rank-list"><li v-for="product in overview.top_products" :key="product.product_id"><span>{{ product.product_name }}</span><small>{{ product.product_id }}</small><strong>{{ number(product.count) }}</strong></li></ol>
            <div v-else class="empty-compact">Немає товарних подій</div>
          </article>
          <article class="panel">
            <div class="panel__heading"><div><span class="eyebrow">КОНТЕНТ</span><h3>Популярні сторінки</h3></div></div>
            <ol v-if="overview.top_pages.length" class="rank-list"><li v-for="page in overview.top_pages" :key="page.page_path"><span class="mono">{{ page.page_path }}</span><strong>{{ number(page.count) }}</strong></li></ol>
            <div v-else class="empty-compact">Немає переглядів сторінок</div>
          </article>
        </section>

        <section class="panel panel--wide events-panel">
          <div class="panel__heading">
            <div><span class="eyebrow">RAW EVENTS</span><h3>Журнал подій</h3></div>
            <span class="panel__meta">{{ number(events.count) }} записів</span>
          </div>
          <div class="table-scroll">
            <table class="events-table">
              <thead><tr><th>Час</th><th>Подія</th><th>Клієнт</th><th>Джерело</th><th>Локація</th><th>Товар / замовлення</th><th></th></tr></thead>
              <tbody>
                <tr v-for="event in events.results" :key="event.event_id">
                  <td class="nowrap">{{ dateTime(event.occurred_at) }}</td>
                  <td><span class="event-badge">{{ eventLabel(event.event_name) }}</span></td>
                  <td>{{ event.client_alias || '—' }}</td>
                  <td><span class="source-badge" :class="`source-badge--${event.source}`">{{ event.source }}</span></td>
                  <td>{{ event.location_uniq_id || event.location_id || '—' }}</td>
                  <td class="mono">{{ event.order_id || event.product_id || '—' }}</td>
                  <td><button class="text-button" @click="selectedEvent = event">Деталі</button></td>
                </tr>
                <tr v-if="!events.results.length"><td colspan="7" class="empty-table">Подій за цими фільтрами не знайдено</td></tr>
              </tbody>
            </table>
          </div>
          <footer class="pagination">
            <button class="button button--subtle" :disabled="events.page <= 1 || loading" @click="changePage(events.page - 1)">← Назад</button>
            <span>Сторінка {{ events.page }} з {{ totalPages }}</span>
            <button class="button button--subtle" :disabled="events.page >= totalPages || loading" @click="changePage(events.page + 1)">Далі →</button>
          </footer>
        </section>
        </div>
      </section>

      <EventDetails v-if="selectedEvent" :event="selectedEvent" @close="selectedEvent = null" />
      <div v-if="loading" class="loading-bar"></div>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import { ApiError, apiGet, exportEventsCsv, getToken, setToken } from "./api";
import BreakdownBars from "./components/BreakdownBars.vue";
import EventDetails from "./components/EventDetails.vue";
import KpiCard from "./components/KpiCard.vue";
import OrderClicksChart from "./components/OrderClicksChart.vue";
import TimelineChart from "./components/TimelineChart.vue";


const pad = (value) => String(value).padStart(2, "0");
const toDateInput = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
const today = new Date();
const monthAgo = new Date(today);
monthAgo.setDate(monthAgo.getDate() - 30);

const emptyFilters = () => ({
  date_from: toDateInput(monthAgo), date_to: toDateInput(today), client_alias: "", source: "", event_name: "",
  location_id: "", location_uniq_id: "", visitor_id: "", session_id: "", customer_id: "", product_id: "",
  order_id: "", booking_id: "", device_type: "", interaction_surface: "", search: "",
});

const emptyOverview = () => ({
  totals: { total_events: 0, visitors: 0, sessions: 0, customers: 0, orders: 0, order_revenue: 0 },
  funnel: [], timeline: [], granularity: "day",
  breakdowns: { events: [], clients: [], sources: [], locations: [] },
  top_products: [], top_pages: [],
  upsell: { block_impressions: 0, product_impressions: 0, clicks: 0, cart_adds: 0, attributed_orders: 0, total_orders: 0, order_share_rate: 0, quantity: 0, revenue: 0, click_to_cart_rate: 0, click_to_order_rate: 0, products: [] },
  mobile_tile: { eligible_sessions: 0, switch_clicks: 0, switched_layout_sessions: 0, switched_to_tile_sessions: 0, switch_rate: 0, returned_to_list_sessions: 0, return_rate: 0, tile_cart_sessions: 0, tile_cart_adds: 0, tile_cart_conversion_rate: 0, mobile_orders: 0, tile_orders: 0, list_orders: 0, final_tile_orders: 0, tile_order_conversion_rate: 0, tile_order_share_rate: 0 },
  click_journey: { orders: 0, average: 0, median: 0, timeline: [] },
  searches: { total: 0, unique: 0, queries: [] },
  order_comments: { total: 0, items: [] },
  booking_comments: { total: 0, items: [] },
});

const tokenInput = ref(getToken());
const connected = ref(false);
const loading = ref(false);
const error = ref("");
const updatedAt = ref(null);
const advancedFilters = ref(false);
const activeTab = ref("overview");
const selectedEvent = ref(null);
const filters = reactive(emptyFilters());
const appliedFilters = ref({ ...filters });
const meta = reactive({ filters: { client_aliases: [], sources: [], event_names: [], locations: [], location_uniq_ids: [], device_types: [], interaction_surfaces: [] } });
const overview = reactive(emptyOverview());
const events = reactive({ count: 0, page: 1, page_size: 50, results: [] });

const dashboardSections = {
  overview: {
    eyebrow: "ОГЛЯД ПОВЕДІНКИ",
    title: "Що роблять користувачі",
    description: "Події, конверсія, замовлення та ефективність блоку «Додати ще».",
  },
  dynamics: {
    eyebrow: "ДИНАМІКА",
    title: "Події та відвідувачі",
    description: "Зміна активності користувачів у вибраному періоді.",
  },
  clicks: {
    eyebrow: "ШЛЯХ ДО ЗАМОВЛЕННЯ",
    title: "Кліки до замовлення",
    description: "Середня та медіанна кількість кліків до успішного оформлення.",
  },
};
const activeSection = computed(() => dashboardSections[activeTab.value] || dashboardSections.overview);

const number = (value) => new Intl.NumberFormat("uk-UA", { maximumFractionDigits: 0 }).format(Number(value) || 0);
const decimal = (value) => new Intl.NumberFormat("uk-UA", { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(Number(value) || 0);
const dateTime = (value) => new Intl.DateTimeFormat("uk-UA", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
const updatedLabel = computed(() => updatedAt.value ? new Intl.DateTimeFormat("uk-UA", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(updatedAt.value) : "—");
const totalPages = computed(() => Math.max(Math.ceil(events.count / events.page_size), 1));
const activeFilterCount = computed(() => Object.entries(filters).filter(([key, value]) => value && !["date_from", "date_to"].includes(key)).length + 2);
const granularityLabel = computed(() => ({ hour: "погодинно", day: "поденно", week: "потижнево" }[overview.granularity] || "поденно"));

const labels = {
  session_started: "Старт сесії", page_viewed: "Перегляд сторінки", page_engagement: "Взаємодія зі сторінкою",
  menu_layout_viewed: "Показ режиму меню", menu_layout_changed: "Змінено режим меню",
  menu_searched: "Пошук", product_viewed: "Перегляд товару", wishlist_item_added: "У бажане", contact_clicked: "Контакт",
  cart_item_added: "Додано в кошик", cart_quantity_changed: "Змінено кількість", cart_item_removed: "Видалено з кошика",
  cart_cleared: "Кошик очищено", checkout_started: "Початок оформлення", order_created: "Замовлення створено",
  booking_created: "Бронювання створено",
  purchase_completed: "Оплату завершено", upsell_block_impression: "Показ OrderMore", upsell_product_impression: "Показ товару OrderMore",
  upsell_product_clicked: "Клік OrderMore", upsell_cart_added: "OrderMore у кошику", upsell_order_attributed: "OrderMore у замовленні",
};
const eventLabel = (name) => labels[name] || name;

const assignReactive = (target, source) => {
  Object.keys(target).forEach((key) => delete target[key]);
  Object.assign(target, source);
};

const queryFilters = () => ({ ...appliedFilters.value });

const loadAll = async ({ includeMeta = true } = {}) => {
  loading.value = true;
  error.value = "";
  try {
    const requests = [
      apiGet("/api/dashboard/overview", queryFilters()),
      apiGet("/api/dashboard/events", { ...queryFilters(), page: events.page, page_size: events.page_size }),
    ];
    if (includeMeta) requests.push(apiGet("/api/dashboard/meta"));
    const [overviewData, eventData, metaData] = await Promise.all(requests);
    assignReactive(overview, overviewData);
    assignReactive(events, eventData);
    if (metaData) assignReactive(meta, metaData);
    updatedAt.value = new Date();
    connected.value = true;
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 401) {
      connected.value = false;
      error.value = "Невірний dashboard token";
    } else {
      error.value = `Не вдалося завантажити аналітику: ${caught.message}`;
    }
  } finally {
    loading.value = false;
  }
};

const connect = async () => {
  setToken(tokenInput.value.trim());
  events.page = 1;
  await loadAll();
};
const logout = () => {
  setToken(""); tokenInput.value = ""; connected.value = false; error.value = "";
};
const refresh = () => loadAll({ includeMeta: false });
const applyFilters = async () => {
  appliedFilters.value = { ...filters };
  events.page = 1;
  await loadAll({ includeMeta: false });
};
const resetFilters = async () => {
  Object.assign(filters, emptyFilters());
  await applyFilters();
};
const changePage = async (page) => {
  events.page = page;
  await loadAll({ includeMeta: false });
  document.querySelector(".events-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
};
const downloadCsv = async () => {
  try { await exportEventsCsv(queryFilters()); }
  catch (caught) { error.value = `Не вдалося експортувати CSV: ${caught.message}`; }
};
const funnelRate = (index) => {
  const first = Number(overview.funnel[0]?.count) || 0;
  return first ? decimal((Number(overview.funnel[index]?.count) || 0) / first * 100) : "0";
};

onMounted(() => {
  if (getToken()) connect();
});
</script>
