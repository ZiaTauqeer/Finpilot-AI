<script setup>
import { computed, onMounted } from 'vue'
import useFinanceData from '../composables/useFinanceData'

const {
  riskSignals,
  emergencyFundMonths,
  profile,
  recommendations,
  opportunities,
  monthEndForecast,
  spendForecast,
  anomalySignals,
  recurringSignals,
  demoScenarios,
  activeDemoScenarioId,
  demoScenarioLoading,
  demoScenarioApplying,
  demoScenarioError,
  refreshDemoScenarios,
  activateDemoScenario,
  categorySummary,
  categoryColor,
  formatCurrency,
} = useFinanceData()

onMounted(() => {
  refreshDemoScenarios()
})

const applyScenario = async (scenarioId) => {
  await activateDemoScenario(scenarioId)
}

const spendChartWidth = 340
const spendChartHeight = 170
const spendChartPadding = {
  top: 16,
  right: 16,
  bottom: 28,
  left: 10,
}

const toSvgPath = (points) => points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')

const spendForecastChart = computed(() => {
  const points = spendForecast.value.chartPoints ?? []
  if (points.length === 0) {
    return {
      points: [],
      historicalPath: '',
      forecastPath: '',
      guideLines: [],
      hasData: false,
    }
  }

  const values = points.map((item) => item.value)
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const valueRange = maxValue - minValue || 1
  const valuePadding = valueRange * 0.2
  const scaledMin = Math.max(minValue - valuePadding, 0)
  const scaledMax = maxValue + valuePadding
  const innerWidth = spendChartWidth - spendChartPadding.left - spendChartPadding.right
  const innerHeight = spendChartHeight - spendChartPadding.top - spendChartPadding.bottom

  const mapY = (value) =>
    spendChartPadding.top + ((scaledMax - value) / Math.max(scaledMax - scaledMin, 1)) * innerHeight

  const positioned = points.map((point, index) => {
    const x =
      points.length > 1
        ? spendChartPadding.left + (index / (points.length - 1)) * innerWidth
        : spendChartPadding.left + innerWidth / 2

    return {
      ...point,
      x,
      y: mapY(point.value),
      displayValue: formatCurrency(point.value),
    }
  })

  const firstForecastIndex = positioned.findIndex((point) => point.isForecast)
  const historicalPoints =
    firstForecastIndex >= 0 ? positioned.slice(0, firstForecastIndex) : positioned
  const forecastPoints =
    firstForecastIndex > 0 ? positioned.slice(firstForecastIndex - 1) : []

  const guideLines = [0, 1, 2, 3].map((step) => {
    const value = scaledMin + ((scaledMax - scaledMin) * step) / 3
    return {
      value,
      y: mapY(value),
      label: formatCurrency(value),
    }
  })

  return {
    points: positioned,
    historicalPath: historicalPoints.length > 1 ? toSvgPath(historicalPoints) : '',
    forecastPath: forecastPoints.length > 1 ? toSvgPath(forecastPoints) : '',
    guideLines,
    hasData: positioned.length > 0,
  }
})
</script>

<template>
  <main class="flex w-full flex-col gap-5 px-4 py-6">
    <section>
      <h1 class="text-xl font-bold tracking-tight text-slate-900">AI Insights</h1>
      <p class="mt-1 text-xs text-slate-500">Predictive analysis and opportunities</p>
    </section>

    <div class="grid grid-cols-2 gap-3">
      <div class="rounded-2xl bg-white p-4 shadow-sm border border-slate-100">
        <p class="text-[10px] font-bold uppercase tracking-wide text-slate-400">Overspending</p>
        <p class="mt-1 text-xl font-bold" :class="riskSignals.overspending ? 'text-rose-600' : 'text-emerald-600'">
          {{ riskSignals.overspending ? 'High' : 'Stable' }}
        </p>
      </div>
      <div class="rounded-2xl bg-white p-4 shadow-sm border border-slate-100">
        <p class="text-[10px] font-bold uppercase tracking-wide text-slate-400">Spike Risk</p>
        <p class="mt-1 text-xl font-bold" :class="riskSignals.discretionarySpike ? 'text-amber-600' : 'text-emerald-600'">
          {{ riskSignals.discretionarySpike ? 'Elevated' : 'Control' }}
        </p>
      </div>
      <div class="rounded-2xl bg-white p-4 shadow-sm border border-slate-100">
        <p class="text-[10px] font-bold uppercase tracking-wide text-slate-400">Runway</p>
        <p class="mt-1 text-xl font-bold text-slate-800">{{ emergencyFundMonths.toFixed(1) }} <span class="text-xs font-medium text-slate-500">mo</span></p>
      </div>
      <div class="rounded-2xl bg-white p-4 shadow-sm border border-slate-100">
        <p class="text-[10px] font-bold uppercase tracking-wide text-slate-400">Target</p>
        <p class="mt-1 text-xl font-bold text-slate-800">{{ profile.emergencyTargetMonths }} <span class="text-xs font-medium text-slate-500">mo</span></p>
      </div>
    </div>

    <section
      class="rounded-2xl border p-4"
      :class="monthEndForecast.status === 'at-risk' ? 'border-rose-200 bg-rose-50' : 'border-emerald-200 bg-emerald-50'"
    >
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-bold text-slate-800">Month-End Outlook</h2>
        <span
          class="rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wider"
          :class="monthEndForecast.status === 'at-risk' ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'"
        >
          {{ monthEndForecast.status === 'at-risk' ? 'At Risk' : 'On Track' }}
        </span>
      </div>
      <p class="mt-2 text-xs text-slate-600">
        Forecast {{ formatCurrency(monthEndForecast.projectedExpenses) }} against {{ formatCurrency(monthEndForecast.monthBudget) }} for {{ monthEndForecast.monthLabel }}.
      </p>
    </section>

    <section class="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5 shadow-sm">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="text-sm font-bold text-slate-800">Spend Forecast</h2>
          <p class="mt-1 text-xs text-slate-600">
            {{ spendForecast.model }} predicts {{ formatCurrency(spendForecast.predictedNextMonth) }} for {{ spendForecast.forecastLabel }}.
          </p>
        </div>
        <div class="rounded-xl border border-indigo-200 bg-white px-3 py-2 text-right shadow-sm">
          <p class="text-[9px] font-bold uppercase tracking-widest text-slate-500">Confidence</p>
          <p class="text-base font-bold text-indigo-700">{{ Math.round(spendForecast.confidence * 100) }}%</p>
        </div>
      </div>

      <div class="mt-4 overflow-hidden rounded-xl border border-indigo-100 bg-white p-2">
        <svg
          v-if="spendForecastChart.hasData"
          :viewBox="`0 0 ${spendChartWidth} ${spendChartHeight}`"
          class="h-44 w-full"
          role="img"
          aria-label="Monthly spend history and forecast chart"
        >
          <line
            v-for="line in spendForecastChart.guideLines"
            :key="`guide-${line.y}`"
            x1="0"
            :x2="spendChartWidth"
            :y1="line.y"
            :y2="line.y"
            stroke="#e2e8f0"
            stroke-width="1"
            stroke-dasharray="4 4"
          />

          <path
            v-if="spendForecastChart.historicalPath"
            :d="spendForecastChart.historicalPath"
            fill="none"
            stroke="#1d4ed8"
            stroke-width="3"
            stroke-linecap="round"
          />

          <path
            v-if="spendForecastChart.forecastPath"
            :d="spendForecastChart.forecastPath"
            fill="none"
            stroke="#7c3aed"
            stroke-width="3"
            stroke-linecap="round"
            stroke-dasharray="7 6"
          />

          <g v-for="point in spendForecastChart.points" :key="`point-${point.label}-${point.monthKey}`">
            <circle
              :cx="point.x"
              :cy="point.y"
              :r="point.isForecast ? 4.5 : 3.5"
              :fill="point.isForecast ? '#7c3aed' : '#1d4ed8'"
            />
            <text
              :x="point.x"
              :y="spendChartHeight - 8"
              text-anchor="middle"
              class="fill-slate-500 text-[10px] font-semibold"
            >
              {{ point.label }}
            </text>
          </g>
        </svg>

        <p v-else class="p-3 text-xs text-slate-500">Not enough data yet to build spend forecast.</p>
      </div>

      <div class="mt-3 grid grid-cols-2 gap-2 text-[11px] text-slate-600">
        <div class="rounded-lg border border-indigo-100 bg-white px-3 py-2">
          Prediction band: {{ formatCurrency(spendForecast.lowerBound) }} - {{ formatCurrency(spendForecast.upperBound) }}
        </div>
        <div class="rounded-lg border border-indigo-100 bg-white px-3 py-2">
          Model not accounting for irregular expenses.
        </div>
      </div>
    </section>

    <section class="rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 p-5 text-white shadow-md">
      <h2 class="text-sm font-bold flex items-center gap-2">
        <span>✨</span> Savings Opportunities
      </h2>
      <div class="mt-4 space-y-3">
        <div v-for="item in opportunities" :key="item.title" class="rounded-xl bg-white/20 p-3 backdrop-blur-md border border-white/20">
          <p class="text-[10px] uppercase tracking-wide text-emerald-100 font-bold">{{ item.title }}</p>
          <p class="mt-0.5 font-display text-2xl font-bold">{{ item.value }}</p>
          <p class="mt-1 text-xs text-emerald-50">{{ item.detail }}</p>
        </div>
      </div>
    </section>

    <section class="rounded-2xl bg-white p-5 shadow-sm border border-slate-100">
      <h2 class="text-sm font-bold text-slate-800 mb-4">Recommendation Queue</h2>
      <div class="space-y-3">
        <div
          v-for="item in recommendations"
          :key="item.title"
          class="flex flex-col gap-1.5 border-b border-slate-100 pb-3 last:border-0 last:pb-0"
        >
          <div class="flex items-center justify-between">
            <p class="text-sm font-bold text-slate-800">{{ item.title }}</p>
            <span
              class="rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider border"
              :class="
                item.priority === 'High'
                  ? 'bg-rose-50 text-rose-600 border-rose-100'
                  : item.priority === 'Medium'
                    ? 'bg-amber-50 text-amber-600 border-amber-100'
                    : 'bg-emerald-50 text-emerald-600 border-emerald-100'
              "
            >
              {{ item.priority }}
            </span>
          </div>
            <p class="text-xs text-slate-500 leading-relaxed">{{ item.detail }}</p>
          </div>
      </div>
    </section>

    <section class="rounded-2xl bg-white p-5 shadow-sm border border-slate-100">
      <h2 class="text-sm font-bold text-slate-800 mb-4">Spending Anomalies</h2>
      <div v-if="anomalySignals.anomalies.length" class="space-y-2">
        <div
          v-for="item in anomalySignals.anomalies.slice(0, 4)"
          :key="item.id"
          class="rounded-xl border border-amber-200 bg-amber-50 p-3"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="text-xs font-bold text-slate-800">{{ item.description }}</p>
            <span class="rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-amber-700">{{ item.severity }}</span>
          </div>
          <p class="mt-1 text-[11px] text-slate-600">{{ item.date }} | {{ item.category }}</p>
          <p class="mt-1 text-xs font-semibold text-amber-800">{{ formatCurrency(item.amount) }} (baseline {{ formatCurrency(item.baseline) }})</p>
        </div>
      </div>
      <p v-else class="text-xs text-slate-500">No unusual spending spikes detected in current history.</p>
    </section>

    <section class="rounded-2xl bg-white p-5 shadow-sm border border-slate-100 mb-4">
      <h2 class="text-sm font-bold text-slate-800 mb-4">Expense Concentration</h2>
      <div class="space-y-4">
        <div v-for="item in categorySummary" :key="item.name">
          <div class="mb-1.5 flex items-center justify-between text-xs font-semibold text-slate-700">
            <span>{{ item.name }}</span>
            <span>{{ formatCurrency(item.amount) }}</span>
          </div>
          <div class="h-1.5 rounded-full bg-slate-100 overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500"
              :class="categoryColor[item.name] || 'bg-cyan-600'"
              :style="{ width: `${item.percent.toFixed(0)}%` }"
            ></div>
          </div>
        </div>
      </div>
    </section>

    <section class="rounded-2xl bg-white p-5 shadow-sm border border-slate-100 mb-4">
      <h2 class="text-sm font-bold text-slate-800 mb-4">Recurring and Subscriptions</h2>
      <div v-if="recurringSignals.recurring.length" class="space-y-2">
        <div
          v-for="item in recurringSignals.recurring"
          :key="item.id"
          class="rounded-xl border border-cyan-100 bg-cyan-50 p-3"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="text-xs font-bold text-slate-800">{{ item.merchant }}</p>
            <span class="rounded-full bg-cyan-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-cyan-700">
              {{ item.subscription ? 'Subscription' : 'Recurring' }}
            </span>
          </div>
          <p class="mt-1 text-[11px] text-slate-600">{{ item.cadence }} cadence | Next expected {{ item.nextExpectedDate }}</p>
          <p class="mt-1 text-xs font-semibold text-cyan-800">Expected {{ formatCurrency(item.predictedAmount) }}</p>
        </div>
      </div>
      <p v-else class="text-xs text-slate-500">No recurring charge patterns found yet.</p>
    </section>
  </main>
</template>
