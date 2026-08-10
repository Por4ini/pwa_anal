<template>
  <div class="details-backdrop" @click.self="$emit('close')">
    <article class="details-panel">
      <header>
        <div>
          <span class="eyebrow">Деталі події</span>
          <h2>{{ event.event_name }}</h2>
        </div>
        <button class="icon-button" @click="$emit('close')">×</button>
      </header>
      <dl class="details-grid">
        <template v-for="item in fields" :key="item.label">
          <dt>{{ item.label }}</dt>
          <dd>{{ item.value || '—' }}</dd>
        </template>
      </dl>
      <h3>Properties</h3>
      <pre>{{ JSON.stringify(event.properties || {}, null, 2) }}</pre>
    </article>
  </div>
</template>

<script setup>
import { computed } from "vue";


const props = defineProps({ event: { type: Object, required: true } });
defineEmits(["close"]);

const fields = computed(() => [
  { label: "Event ID", value: props.event.event_id },
  { label: "Час події", value: new Date(props.event.occurred_at).toLocaleString("uk-UA") },
  { label: "Клієнт", value: props.event.client_alias },
  { label: "Джерело", value: props.event.source },
  { label: "Локація", value: props.event.location_uniq_id || props.event.location_id },
  { label: "Відвідувач", value: props.event.visitor_id },
  { label: "Сесія", value: props.event.session_id },
  { label: "Користувач", value: props.event.customer_id },
  { label: "Товар", value: props.event.product_id },
  { label: "Замовлення", value: props.event.order_id },
  { label: "Сторінка", value: props.event.page_path },
  { label: "Referrer", value: props.event.referrer_path },
  { label: "User agent", value: props.event.user_agent },
]);
</script>

