<script setup>
import { ref } from 'vue'
import useFinanceData from '../composables/useFinanceData'

const {
  bucketAllocation,
  totalIncome,
  profile,
  budgetUsedPercent,
  recommendations,
  formatCurrency,
  bucketColor,
  updateBucketSettings,
  resetBucketLimit,
} = useFinanceData()

const editingBucketId = ref(null)
const editName = ref('')
const editLimit = ref('')
const editError = ref('')

const openBucketEditor = (bucket) => {
  if (editingBucketId.value === bucket.id) {
    editingBucketId.value = null
    editError.value = ''
    return
  }

  editingBucketId.value = bucket.id
  editName.value = bucket.name
  editLimit.value = Number(bucket.allocated).toFixed(0)
  editError.value = ''
}

const saveBucketEditor = () => {
  if (!editingBucketId.value) {
    return
  }

  const result = updateBucketSettings(editingBucketId.value, {
    name: editName.value,
    limit: editLimit.value,
  })

  if (!result.ok) {
    editError.value = result.error
    return
  }

  editingBucketId.value = null
  editError.value = ''
}

const restoreAutoLimit = () => {
  if (!editingBucketId.value) {
    return
  }

  resetBucketLimit(editingBucketId.value)
  editingBucketId.value = null
  editError.value = ''
}
</script>

<template>
  <main class="flex w-full flex-col gap-5 px-4 py-6">
    <section>
      <h1 class="text-xl font-bold tracking-tight text-slate-900">Buckets</h1>
      <p class="mt-1 text-xs text-slate-500">Auto-allocated spending envelopes</p>

      <div class="mt-4 flex flex-wrap gap-2 text-[10px] font-semibold text-slate-600">
        <span class="rounded-full bg-cyan-50 px-3 py-1.5 border border-cyan-100 text-cyan-800">Income: {{ formatCurrency(totalIncome) }}</span>
        <span class="rounded-full bg-slate-100 px-3 py-1.5 border border-slate-200">Usage: {{ budgetUsedPercent.toFixed(0) }}%</span>
        <span class="rounded-full bg-purple-50 px-3 py-1.5 border border-purple-100 text-purple-800">{{ profile.label }}</span>
      </div>
    </section>

    <section class="flex flex-col gap-3">
      <article
        v-for="bucket in bucketAllocation"
        :key="bucket.id"
        class="rounded-2xl bg-white p-4 shadow-sm border border-slate-100 cursor-pointer"
        @click="openBucketEditor(bucket)"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <div class="h-8 w-8 rounded-full flex items-center justify-center text-xs" :class="bucketColor[bucket.name] || 'bg-cyan-100 text-cyan-700'">
               📁
            </div>
            <h2 class="font-bold text-slate-800">{{ bucket.name }}</h2>
          </div>
          <span
            class="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider"
            :class="bucket.utilization > 100 ? 'bg-rose-50 text-rose-600 border border-rose-100' : 'bg-emerald-50 text-emerald-600 border border-emerald-100'"
          >
            {{ bucket.utilization.toFixed(0) }}%
          </span>
        </div>

        <p class="mb-2 text-[10px] font-semibold text-cyan-700" v-if="editingBucketId === bucket.id">Editing bucket settings</p>
        
        <div class="flex items-end justify-between text-xs mb-2">
          <div class="flex flex-col gap-0.5">
            <span class="text-slate-400">Spent / Allocated</span>
            <span class="font-medium text-slate-700">{{ formatCurrency(bucket.spent) }} <span class="text-slate-300">/</span> {{ formatCurrency(bucket.allocated) }}</span>
          </div>
          <div class="flex flex-col items-end gap-0.5">
            <span class="text-slate-400">Left</span>
            <span class="font-bold" :class="bucket.remaining >= 0 ? 'text-emerald-600' : 'text-rose-600'">
              {{ formatCurrency(bucket.remaining) }}
            </span>
          </div>
        </div>

        <div class="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-500"
            :class="bucket.utilization > 100 ? 'bg-rose-500' : 'bg-cyan-500'"
            :style="{ width: `${Math.min(bucket.utilization, 100)}%` }"
          ></div>
        </div>

        <form
          v-if="editingBucketId === bucket.id"
          class="mt-3 space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3"
          @submit.prevent="saveBucketEditor"
          @click.stop
        >
          <label class="block">
            <span class="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Bucket name</span>
            <input
              v-model="editName"
              type="text"
              class="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 outline-none focus:border-cyan-500"
            />
          </label>
          <label class="block">
            <span class="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Budget limit (INR)</span>
            <input
              v-model="editLimit"
              type="number"
              min="0"
              step="1"
              class="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 outline-none focus:border-cyan-500"
            />
          </label>
          <p v-if="editError" class="text-[10px] font-semibold text-rose-600">{{ editError }}</p>
          <div class="flex flex-wrap gap-2 pt-1">
            <button type="submit" class="rounded-full bg-cyan-600 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide text-white">Save</button>
            <button type="button" class="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-600" @click="restoreAutoLimit">
              Auto Limit
            </button>
          </div>
        </form>
      </article>
    </section>

    <section class="mt-2 rounded-2xl bg-gradient-to-br from-slate-800 to-slate-900 p-5 shadow-lg text-white">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-sm font-bold">Automation Playbook</h2>
          <p class="text-[10px] text-slate-400 mt-0.5">AI-driven bucket insights</p>
        </div>
        <RouterLink to="/insights" class="rounded-full bg-white/10 px-3 py-1.5 text-[10px] font-bold transition hover:bg-white/20">
          More
        </RouterLink>
      </div>
      
      <div class="flex flex-col gap-3">
        <div
          v-for="item in recommendations.slice(0, 2)"
          :key="item.title"
          class="flex items-start gap-3 rounded-xl bg-white/5 p-3"
        >
          <div class="mt-0.5 text-lg">💡</div>
          <div>
            <p class="text-xs font-bold text-white">{{ item.title }}</p>
            <p class="mt-1 text-[10px] text-slate-300 leading-relaxed">{{ item.detail }}</p>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>
