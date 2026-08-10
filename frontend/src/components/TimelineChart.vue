<template>
  <div v-if="points.length" class="timeline-chart">
    <div class="timeline-chart__legend">
      <span><i class="dot dot--events"></i>Події</span>
      <span><i class="dot dot--visitors"></i>Відвідувачі</span>
    </div>
    <svg viewBox="0 0 960 280" role="img" aria-label="Динаміка подій та відвідувачів">
      <g class="timeline-chart__grid">
        <line v-for="index in 5" :key="index" x1="56" x2="940" :y1="30 + (index - 1) * 52" :y2="30 + (index - 1) * 52" />
      </g>
      <path class="timeline-chart__area" :d="areaPath" />
      <path class="timeline-chart__line timeline-chart__line--events" :d="eventPath" />
      <path class="timeline-chart__line timeline-chart__line--visitors" :d="visitorPath" />
      <g v-for="(point, index) in normalized" :key="point.bucket">
        <circle class="timeline-chart__point" :cx="point.x" :cy="point.eventsY" r="4">
          <title>{{ formatBucket(point.bucket) }}: {{ point.events }} подій</title>
        </circle>
      </g>
      <text x="56" y="272">{{ formatBucket(points[0].bucket) }}</text>
      <text x="498" y="272" text-anchor="middle">{{ formatBucket(points[Math.floor(points.length / 2)].bucket) }}</text>
      <text x="940" y="272" text-anchor="end">{{ formatBucket(points[points.length - 1].bucket) }}</text>
    </svg>
  </div>
  <div v-else class="empty-chart">Події з’являться тут після першого збору даних</div>
</template>

<script setup>
import { computed } from "vue";


const props = defineProps({ points: { type: Array, default: () => [] } });

const normalized = computed(() => {
  const max = Math.max(...props.points.map((point) => Number(point.events) || 0), 1);
  const count = Math.max(props.points.length - 1, 1);
  return props.points.map((point, index) => ({
    ...point,
    x: 56 + (index / count) * 884,
    eventsY: 238 - ((Number(point.events) || 0) / max) * 208,
    visitorsY: 238 - ((Number(point.visitors) || 0) / max) * 208,
  }));
});

const buildPath = (key) => normalized.value.map((point, index) => `${index ? "L" : "M"}${point.x},${point[key]}`).join(" ");
const eventPath = computed(() => buildPath("eventsY"));
const visitorPath = computed(() => buildPath("visitorsY"));
const areaPath = computed(() => {
  if (!normalized.value.length) return "";
  return `${eventPath.value} L${normalized.value.at(-1).x},238 L${normalized.value[0].x},238 Z`;
});
const formatBucket = (value) => new Intl.DateTimeFormat("uk-UA", {
  day: "2-digit",
  month: "short",
  hour: props.points.length <= 48 ? "2-digit" : undefined,
  minute: props.points.length <= 48 ? "2-digit" : undefined,
}).format(new Date(value));
</script>

