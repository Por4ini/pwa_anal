<template>
  <div v-if="points.length" class="timeline-chart order-clicks-chart">
    <div class="timeline-chart__legend">
      <span><i class="dot dot--average"></i>Середнє</span>
      <span><i class="dot dot--median"></i>Медіана</span>
    </div>
    <svg viewBox="0 0 960 280" role="img" aria-label="Кліки до замовлення">
      <g class="timeline-chart__grid">
        <line v-for="index in 5" :key="index" x1="56" x2="940" :y1="30 + (index - 1) * 52" :y2="30 + (index - 1) * 52" />
      </g>
      <path class="timeline-chart__line timeline-chart__line--average" :d="averagePath" />
      <path class="timeline-chart__line timeline-chart__line--median" :d="medianPath" />
      <g v-for="point in normalized" :key="point.bucket">
        <circle class="timeline-chart__point timeline-chart__point--average" :cx="point.x" :cy="point.averageY" r="4">
          <title>{{ formatBucket(point.bucket) }}: середнє {{ point.average }}, медіана {{ point.median }}, {{ point.orders }} замовлень</title>
        </circle>
      </g>
      <text x="56" y="272">{{ formatBucket(points[0].bucket) }}</text>
      <text x="498" y="272" text-anchor="middle">{{ formatBucket(points[Math.floor(points.length / 2)].bucket) }}</text>
      <text x="940" y="272" text-anchor="end">{{ formatBucket(points[points.length - 1].bucket) }}</text>
    </svg>
  </div>
  <div v-else class="empty-chart">Графік з’явиться після замовлень із новим лічильником</div>
</template>

<script setup>
import { computed } from "vue";


const props = defineProps({ points: { type: Array, default: () => [] } });

const normalized = computed(() => {
  const max = Math.max(...props.points.flatMap((point) => [Number(point.average) || 0, Number(point.median) || 0]), 1);
  const count = Math.max(props.points.length - 1, 1);
  return props.points.map((point, index) => ({
    ...point,
    x: 56 + (index / count) * 884,
    averageY: 238 - ((Number(point.average) || 0) / max) * 208,
    medianY: 238 - ((Number(point.median) || 0) / max) * 208,
  }));
});

const buildPath = (key) => normalized.value.map((point, index) => `${index ? "L" : "M"}${point.x},${point[key]}`).join(" ");
const averagePath = computed(() => buildPath("averageY"));
const medianPath = computed(() => buildPath("medianY"));
const formatBucket = (value) => new Intl.DateTimeFormat("uk-UA", {
  day: "2-digit",
  month: "short",
  hour: props.points.length <= 48 ? "2-digit" : undefined,
  minute: props.points.length <= 48 ? "2-digit" : undefined,
}).format(new Date(value));
</script>
