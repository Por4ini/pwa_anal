<template>
  <article class="kpi-card" :class="tone ? `kpi-card--${tone}` : ''">
    <div class="kpi-card__icon">{{ icon }}</div>
    <div>
      <p class="kpi-card__label">{{ label }}</p>
      <strong class="kpi-card__value">{{ value }}</strong>
      <small v-if="hint" class="kpi-card__hint">{{ hint }}</small>
    </div>
  </article>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  hint: { type: String, default: "" },
  icon: { type: String, default: "•" },
  tone: { type: String, default: "" },
});
</script>

