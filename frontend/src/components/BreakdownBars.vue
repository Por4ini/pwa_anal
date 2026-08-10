<template>
  <div v-if="items.length" class="breakdown-bars">
    <div v-for="item in items" :key="item.label" class="breakdown-bars__row">
      <div class="breakdown-bars__caption">
        <span :title="item.label">{{ item.label }}</span>
        <strong>{{ formatNumber(item.count) }}</strong>
      </div>
      <div class="breakdown-bars__track">
        <div class="breakdown-bars__fill" :style="{ width: `${Math.max((item.count / maximum) * 100, 2)}%` }"></div>
      </div>
    </div>
  </div>
  <div v-else class="empty-compact">Немає даних за обраний період</div>
</template>

<script setup>
import { computed } from "vue";


const props = defineProps({
  items: { type: Array, default: () => [] },
});

const maximum = computed(() => Math.max(...props.items.map((item) => Number(item.count) || 0), 1));
const formatNumber = (value) => new Intl.NumberFormat("uk-UA").format(value || 0);
</script>

