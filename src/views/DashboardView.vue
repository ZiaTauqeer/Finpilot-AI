<script setup>
import useFinanceData from '../composables/useFinanceData'

const {
  profile,
  totalIncome,
  totalExpenses,
  netFlow,
  budgetLimit,
  budgetUsedPercent,
  savingsRate,
  financialHealthScore,
  monthlyTrend,
  maxTrendValue,
  monthEndForecast,
  recommendations,
  formatCurrency,
} = useFinanceData()
</script>

<template>
  <main class="flex w-full flex-col gap-5 px-4 py-6">
    <section class="rounded-3xl bg-gradient-to-br from-cyan-600 to-blue-700 p-6 text-white shadow-lg">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-xs font-medium text-cyan-100 uppercase tracking-wider">Net Flow</p>
          <h1 class="mt-1 font-display text-4xl font-bold">{{ formatCurrency(netFlow) }}</h1>
        </div>
        <div class="h-12 w-12 rounded-full bg-white/20 p-2 backdrop-blur-sm">
          <svg class="h-full w-full text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      </div>
      <div class="mt-6 flex items-center justify-between border-t border-white/20 pt-4 text-sm font-medium">
        <div class="flex flex-col">
          <span class="text-cyan-100">Income</span>
          <span>{{ formatCurrency(totalIncome) }}</span>
        </div>
        <div class="flex flex-col text-right">
          <span class="text-cyan-100">Expenses</span>
          <span>{{ formatCurrency(totalExpenses) }}</span>
        </div>
      </div>
    </section>

    <div class="grid grid-cols-2 gap-4">
      <article class="rounded-2xl bg-white p-4 shadow-sm border border-slate-100 text-center">
        <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Budget</p>
        <p class="mt-2 font-display text-2xl font-semibold text-slate-800">{{ budgetUsedPercent.toFixed(0) }}%</p>
        <div class="mx-auto mt-3 h-1.5 w-full rounded-full bg-slate-100">
          <div class="h-full rounded-full bg-cyan-600" :style="{ width: `${budgetUsedPercent}%` }"></div>
        </div>
        <p class="mt-2 text-[10px] font-medium text-slate-500">Cap {{ formatCurrency(budgetLimit) }}</p>
      </article>

      <article class="rounded-2xl bg-white p-4 shadow-sm border border-slate-100 text-center">
        <p class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Savings Rate</p>
        <p class="mt-2 font-display text-2xl font-semibold text-slate-800">{{ savingsRate.toFixed(1) }}%</p>
        <div class="mx-auto mt-2 flex h-8 w-8 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
        </div>
        <p class="mt-2 text-[10px] font-medium text-slate-500">Aligned with goal</p>
      </article>
    </div>

    <section
      class="rounded-2xl border p-5 shadow-sm"
      :class="
        monthEndForecast.status === 'at-risk'
          ? 'border-rose-200 bg-rose-50/70'
          : 'border-emerald-200 bg-emerald-50/70'
      "
    >
      <div class="flex items-start justify-between gap-3">
        <div>
          <p class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Month-end forecast</p>
          <h2 class="mt-1 text-sm font-bold text-slate-900">{{ monthEndForecast.monthLabel }}</h2>
        </div>
        <span
          class="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider"
          :class="
            monthEndForecast.status === 'at-risk'
              ? 'bg-rose-100 text-rose-700'
              : 'bg-emerald-100 text-emerald-700'
          "
        >
          {{ monthEndForecast.status === 'at-risk' ? 'At Risk' : 'On Track' }}
        </span>
      </div>

      <div class="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div class="rounded-xl bg-white/80 p-3 border border-white">
          <p class="text-slate-500">Projected spend</p>
          <p class="mt-1 text-sm font-bold text-slate-800">{{ formatCurrency(monthEndForecast.projectedExpenses) }}</p>
        </div>
        <div class="rounded-xl bg-white/80 p-3 border border-white">
          <p class="text-slate-500">Budget target</p>
          <p class="mt-1 text-sm font-bold text-slate-800">{{ formatCurrency(monthEndForecast.monthBudget) }}</p>
        </div>
      </div>

      <p class="mt-3 text-xs font-medium" :class="monthEndForecast.status === 'at-risk' ? 'text-rose-700' : 'text-emerald-700'">
        {{
          monthEndForecast.status === 'at-risk'
            ? `Projected overrun ${formatCurrency(Math.abs(monthEndForecast.budgetDelta))}.`
            : `Projected headroom ${formatCurrency(monthEndForecast.budgetDelta)}.`
        }}
      </p>
    </section>

    <section class="rounded-2xl bg-white p-5 shadow-sm border border-slate-100">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-bold text-slate-800">Health Score</h2>
        <div class="rounded-full bg-cyan-50 px-2 py-1 text-[10px] font-bold text-cyan-700 uppercase">Diagnostics</div>
      </div>
      <div class="flex items-center gap-4">
        <div
          class="relative grid h-16 w-16 place-items-center rounded-full text-xs font-bold shadow-inner"
          :style="{ background: `conic-gradient(#0891b2 ${financialHealthScore}%, #f1f5f9 ${financialHealthScore}% 100%)` }"
        >
          <span class="grid h-12 w-12 place-items-center rounded-full bg-white text-lg">{{ financialHealthScore }}</span>
        </div>
        <p class="flex-1 text-xs text-slate-500 font-medium">
          Your budget limits, buckets, and reserve strategies look great! Keep optimizing.
        </p>
      </div>
    </section>

    <section class="mb-4 rounded-2xl bg-white p-5 shadow-sm border border-slate-100 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-bold text-slate-800">Spending Trends</h2>
          <button class="text-[10px] font-bold uppercase text-cyan-600">See All</button>
        </div>
        <div class="space-y-3">
          <div
            v-for="month in monthlyTrend"
            :key="month.label"
            class="flex items-center gap-3 text-xs"
          >
            <p class="w-8 font-semibold text-slate-500">{{ month.label }}</p>
            <div class="flex-1 space-y-1.5">
              <div class="flex h-1.5 overflow-hidden rounded-full bg-slate-100">
                <div class="bg-emerald-500" :style="{ width: `${(month.income / maxTrendValue) * 100}%` }"></div>
              </div>
              <div class="flex h-1.5 overflow-hidden rounded-full bg-slate-100">
                <div class="bg-rose-500" :style="{ width: `${(month.expenses / maxTrendValue) * 100}%` }"></div>
              </div>
            </div>
          </div>
        </div>
    </section>
  </main>
</template>
