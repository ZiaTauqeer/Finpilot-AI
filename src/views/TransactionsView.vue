<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import useFinanceData from '../composables/useFinanceData'
import resolveBackendBaseUrl from '../utils/backendUrl'

const {
  profiledTransactionsWithSignals,
  anomalySignals,
  editableBucketNames,
  assignTransactionBucket,
  formatCurrency,
} = useFinanceData()

const backendBaseUrl = resolveBackendBaseUrl(import.meta.env.VITE_SMS_BACKEND_BASE_URL)

const activeFilter = ref('All')
const selectedTransactionId = ref(null)
const selectedReceiptFile = ref(null)
const receiptAnalyzing = ref(false)
const receiptError = ref('')
const receiptResult = ref(null)
const receiptFeatureStatus = ref({ configured: false, model: '' })
const previousReceiptSnapshot = ref(null)
const selectedReportMonth = ref('')
const reportDownloading = ref(false)
const reportError = ref('')

const RECEIPT_SNAPSHOT_KEY = 'finance:last-receipt-analysis'

const filters = computed(() => ['All', 'Income', ...editableBucketNames.value])

watch(filters, (nextFilters) => {
  if (!nextFilters.includes(activeFilter.value)) {
    activeFilter.value = 'All'
  }
})

const sortedTransactions = computed(() =>
  [...profiledTransactionsWithSignals.value].sort((a, b) => {
    const left = a.occurredAt ?? `${a.date}T00:00:00Z`
    const right = b.occurredAt ?? `${b.date}T00:00:00Z`
    return right.localeCompare(left)
  }),
)

const availableReportMonths = computed(() => {
  const monthSet = new Set()

  for (const tx of profiledTransactionsWithSignals.value) {
    const isoDate = tx.occurredAt?.slice(0, 10) ?? tx.date
    if (/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) {
      monthSet.add(isoDate.slice(0, 7))
    }
  }

  return [...monthSet].sort((a, b) => b.localeCompare(a))
})

const monthLabel = (monthKey) => {
  const [year, month] = monthKey.split('-')
  const monthDate = new Date(Number(year), Number(month) - 1, 1)
  return monthDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}

const visibleTransactions = computed(() => {
  if (activeFilter.value === 'All') {
    return sortedTransactions.value
  }

  if (activeFilter.value === 'Income') {
    return sortedTransactions.value.filter((tx) => tx.direction === 'in')
  }

  return sortedTransactions.value.filter((tx) => tx.bucket === activeFilter.value)
})

watch(
  availableReportMonths,
  (months) => {
    if (!selectedReportMonth.value || !months.includes(selectedReportMonth.value)) {
      selectedReportMonth.value = months[0] ?? ''
    }
  },
  { immediate: true },
)

const downloadMonthlyReport = async () => {
  reportError.value = ''

  if (!selectedReportMonth.value) {
    reportError.value = 'Select a month to download the report.'
    return
  }

  const payloadTransactions = profiledTransactionsWithSignals.value.map((tx) => ({
    date: tx.occurredAt?.slice(0, 10) ?? tx.date,
    description: tx.description,
    amount: Number(tx.amount) || 0,
    direction: tx.direction,
    category: tx.category ?? 'Other',
    bucket: tx.bucket ?? 'Misc',
  }))

  reportDownloading.value = true
  try {
    const response = await fetch(`${backendBaseUrl}/reports/monthly-spend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        month: selectedReportMonth.value,
        currency: 'INR',
        transactions: payloadTransactions,
      }),
    })

    if (!response.ok) {
      let detail = `HTTP ${response.status}`
      try {
        const errorPayload = await response.json()
        detail = String(errorPayload.detail ?? detail)
      } catch {
        // Ignore malformed backend error payloads.
      }
      throw new Error(detail)
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `monthly-spend-${selectedReportMonth.value}.pdf`
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    reportError.value = `Download failed: ${error.message}`
  } finally {
    reportDownloading.value = false
  }
}

const openBucketPicker = (tx) => {
  if (tx.direction !== 'out') {
    return
  }

  selectedTransactionId.value = selectedTransactionId.value === tx.id ? null : tx.id
}

const saveBucketForTransaction = (bucketName) => {
  if (selectedTransactionId.value == null) {
    return
  }

  assignTransactionBucket(selectedTransactionId.value, bucketName)
  selectedTransactionId.value = null
}

const formatUnitCost = (item) => {
  if (!item?.cost_per_unit || !item?.unit_label) {
    return 'n/a'
  }
  return `${formatCurrency(item.cost_per_unit)} ${item.unit_label}`
}

const normalizeItemKey = (name) =>
  String(name ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const readReceiptSnapshot = () => {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const raw = window.sessionStorage.getItem(RECEIPT_SNAPSHOT_KEY)
    if (!raw) {
      return null
    }

    const parsed = JSON.parse(raw)
    if (!parsed || !Array.isArray(parsed.items)) {
      return null
    }

    return parsed
  } catch {
    return null
  }
}

const saveReceiptSnapshot = (payload) => {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.sessionStorage.setItem(
      RECEIPT_SNAPSHOT_KEY,
      JSON.stringify({
        analyzed_at: payload.analyzed_at,
        bill_date: payload.bill_date,
        merchant: payload.merchant,
        currency: payload.currency,
        items: Array.isArray(payload.items) ? payload.items : [],
      }),
    )
  } catch {
    // Ignore session storage failures in privacy-restricted browsers.
  }
}

const buildCostComparisons = (currentItems, previousItems) => {
  const previousByKey = new Map()

  for (const item of previousItems ?? []) {
    const key = normalizeItemKey(item?.name)
    const unitCost = Number(item?.cost_per_unit)
    const perItemCost = Number(item?.cost_per_item)
    if (!key) {
      continue
    }

    previousByKey.set(key, {
      name: item.name,
      cost_per_unit: Number.isFinite(unitCost) && unitCost > 0 ? unitCost : null,
      cost_per_item: Number.isFinite(perItemCost) && perItemCost > 0 ? perItemCost : null,
      unit_label: item.unit_label,
    })
  }

  const betterUnit = []
  const worseUnit = []
  const betterPerItem = []
  const worsePerItem = []

  for (const item of currentItems ?? []) {
    const key = normalizeItemKey(item?.name)
    const currentUnitCost = Number(item?.cost_per_unit)
    const currentPerItemCost = Number(item?.cost_per_item)
    if (!key) {
      continue
    }

    const previous = previousByKey.get(key)
    if (!previous) {
      continue
    }

    if (
      Number.isFinite(currentPerItemCost) &&
      currentPerItemCost > 0 &&
      Number.isFinite(previous.cost_per_item) &&
      previous.cost_per_item > 0
    ) {
      const perItemDelta = currentPerItemCost - previous.cost_per_item
      if (Math.abs(perItemDelta) >= 1e-9) {
        const percentChange = Math.abs((perItemDelta / previous.cost_per_item) * 100)
        const comparison = {
          name: item.name,
          current_cost_per_item: currentPerItemCost,
          previous_cost_per_item: previous.cost_per_item,
          percent_change: Number(percentChange.toFixed(2)),
        }

        if (perItemDelta < 0) {
          betterPerItem.push(comparison)
        } else {
          worsePerItem.push(comparison)
        }
      }
    }

    if (
      Number.isFinite(currentUnitCost) &&
      currentUnitCost > 0 &&
      Number.isFinite(previous.cost_per_unit) &&
      previous.cost_per_unit > 0
    ) {
      const unitDelta = currentUnitCost - previous.cost_per_unit
      if (Math.abs(unitDelta) >= 1e-9) {
        const percentChange = Math.abs((unitDelta / previous.cost_per_unit) * 100)
        const comparison = {
          name: item.name,
          current_cost_per_unit: currentUnitCost,
          previous_cost_per_unit: previous.cost_per_unit,
          unit_label: item.unit_label || previous.unit_label || 'per unit',
          percent_change: Number(percentChange.toFixed(2)),
        }

        if (unitDelta < 0) {
          betterUnit.push(comparison)
        } else {
          worseUnit.push(comparison)
        }
      }
    }
  }

  betterUnit.sort((a, b) => b.percent_change - a.percent_change)
  worseUnit.sort((a, b) => b.percent_change - a.percent_change)
  betterPerItem.sort((a, b) => b.percent_change - a.percent_change)
  worsePerItem.sort((a, b) => b.percent_change - a.percent_change)

  return {
    betterUnit,
    worseUnit,
    betterPerItem,
    worsePerItem,
  }
}

const loadReceiptFeatureStatus = async () => {
  try {
    const response = await fetch(`${backendBaseUrl}/receipts/status`)
    if (!response.ok) {
      throw new Error(`Status HTTP ${response.status}`)
    }

    const payload = await response.json()
    receiptFeatureStatus.value = {
      configured: Boolean(payload.configured),
      model: String(payload.model ?? ''),
    }
  } catch {
    receiptFeatureStatus.value = {
      configured: false,
      model: '',
    }
  }
}

const onReceiptFileChange = (event) => {
  receiptError.value = ''
  const file = event.target?.files?.[0] ?? null
  selectedReceiptFile.value = file
}

const analyzeReceipt = async () => {
  receiptError.value = ''

  if (!selectedReceiptFile.value) {
    receiptError.value = 'Select a receipt image first.'
    return
  }

  const formData = new FormData()
  formData.append('file', selectedReceiptFile.value)

  receiptAnalyzing.value = true
  try {
    const response = await fetch(`${backendBaseUrl}/receipts/analyze`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      let backendDetail = `HTTP ${response.status}`
      try {
        const errorPayload = await response.json()
        backendDetail = String(errorPayload.detail ?? backendDetail)
      } catch {
        // Ignore malformed error payloads.
      }
      throw new Error(backendDetail)
    }

    const payload = await response.json()
    const previousSnapshot = readReceiptSnapshot()
    previousReceiptSnapshot.value = previousSnapshot

    const comparisons = buildCostComparisons(payload.items ?? [], previousSnapshot?.items ?? [])

    receiptResult.value = {
      ...payload,
      insights: {
        ...(payload.insights ?? {}),
        better_unit_cost_items: comparisons.betterUnit,
        worse_unit_cost_items: comparisons.worseUnit,
        better_per_item_items: comparisons.betterPerItem,
        worse_per_item_items: comparisons.worsePerItem,
      },
    }

    saveReceiptSnapshot(payload)
  } catch (error) {
    receiptError.value = `Receipt analysis failed: ${error.message}`
  } finally {
    receiptAnalyzing.value = false
  }
}

onMounted(() => {
  loadReceiptFeatureStatus()
  previousReceiptSnapshot.value = readReceiptSnapshot()
})
</script>

<template>
  <main class="flex w-full flex-col gap-5 px-4 py-6">
    <section>
      <h1 class="text-xl font-bold tracking-tight text-slate-900">Transactions</h1>
      <p class="mt-1 text-xs text-slate-500">Auto-categorized spending feed</p>

      <div class="mt-3 rounded-xl border border-sky-200 bg-sky-50 p-3">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p class="text-xs font-semibold text-sky-900">Monthly Spend PDF</p>
            <p class="text-[11px] text-sky-700">Choose a month and download a styled ReportLab summary.</p>
          </div>

          <div class="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
            <select
              v-model="selectedReportMonth"
              class="min-w-[180px] rounded-lg border border-sky-300 bg-white px-3 py-2 text-xs font-medium text-slate-700"
            >
              <option v-for="month in availableReportMonths" :key="month" :value="month">
                {{ monthLabel(month) }}
              </option>
            </select>

            <button
              type="button"
              class="rounded-lg bg-sky-700 px-4 py-2 text-xs font-semibold text-white transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              :disabled="reportDownloading || !selectedReportMonth"
              @click="downloadMonthlyReport"
            >
              {{ reportDownloading ? 'Preparing PDF...' : 'Download PDF' }}
            </button>
          </div>
        </div>
        <p v-if="reportError" class="mt-2 text-xs font-medium text-rose-600">{{ reportError }}</p>
      </div>
      
      <div class="mt-4 flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
        <button
          v-for="item in filters"
          :key="item"
          type="button"
          class="whitespace-nowrap rounded-full px-4 py-1.5 text-xs font-semibold transition-colors border"
          :class="activeFilter === item ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'"
          @click="activeFilter = item"
        >
          {{ item }}
        </button>
      </div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 class="text-sm font-bold text-slate-800">Bill Analyzer</h2>
          <p class="mt-1 text-xs text-slate-500">
            Upload a bill image to extract line items, per-item pricing, and cost-per-gram/ml insights.
          </p>
        </div>
        <span
          class="rounded-full px-2.5 py-1 text-[11px] font-semibold"
          :class="
            receiptFeatureStatus.configured
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-amber-100 text-amber-700'
          "
        >
        </span>
      </div>

      <div class="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="file"
          accept="image/*"
          class="block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-800 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-white hover:file:bg-slate-700"
          @change="onReceiptFileChange"
        />
        <button
          type="button"
          class="rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          :disabled="receiptAnalyzing || !selectedReceiptFile"
          @click="analyzeReceipt"
        >
          {{ receiptAnalyzing ? 'Analyzing...' : 'Analyze Receipt' }}
        </button>
      </div>

      <p v-if="receiptError" class="mt-2 text-xs font-medium text-rose-600">{{ receiptError }}</p>

      <div v-if="receiptResult" class="mt-4 space-y-4">
        <div class="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p class="text-xs font-semibold text-slate-700">
            {{ receiptResult.merchant || 'Unknown Merchant' }}
            <span class="mx-1 text-slate-300">|</span>
            {{ receiptResult.bill_date || 'Date not detected' }}
          </p>
          <p class="mt-1 text-[11px] text-slate-500">
            {{ receiptResult.items?.length || 0 }} items extracted • Currency {{ receiptResult.currency || 'INR' }}
          </p>
        </div>

        <div class="overflow-x-auto rounded-xl border border-slate-200">
          <table class="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead class="bg-slate-50 text-slate-600">
              <tr>
                <th class="px-3 py-2 font-semibold">Item</th>
                <th class="px-3 py-2 font-semibold">Category</th>
                <th class="px-3 py-2 font-semibold">Qty</th>
                <th class="px-3 py-2 font-semibold">Total</th>
                <th class="px-3 py-2 font-semibold">Per Item</th>
                <th class="px-3 py-2 font-semibold">Per Gram/ml</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 bg-white text-slate-700">
              <tr v-for="item in receiptResult.items" :key="`receipt-${item.name}-${item.total_price}`">
                <td class="px-3 py-2 font-medium text-slate-800">{{ item.name }}</td>
                <td class="px-3 py-2">{{ item.category || 'Other' }}</td>
                <td class="px-3 py-2">{{ item.quantity }}</td>
                <td class="px-3 py-2">{{ formatCurrency(item.total_price) }}</td>
                <td class="px-3 py-2">{{ formatCurrency(item.cost_per_item) }}</td>
                <td class="px-3 py-2">{{ formatUnitCost(item) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="grid gap-3 lg:grid-cols-2">
          <article class="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
            <h3 class="text-[11px] font-bold uppercase tracking-wide text-emerald-700">Better Than Previous Bill</h3>
            <p
              v-if="!previousReceiptSnapshot"
              class="mt-2 text-xs text-emerald-800"
            >
              Upload another bill to compare same-item costs.
            </p>

            <div v-else class="mt-2 space-y-2 text-xs text-emerald-800">
              <p class="font-semibold text-emerald-700">Per Item Cost</p>
              <p v-if="!receiptResult.insights?.better_per_item_items?.length">No per-item improvement found.</p>
              <ul v-else class="space-y-2">
                <li
                  v-for="entry in receiptResult.insights.better_per_item_items"
                  :key="`better-item-${entry.name}-${entry.current_cost_per_item}`"
                  class="rounded-lg bg-white/80 px-2 py-1.5"
                >
                  {{ entry.name }} {{ formatCurrency(entry.current_cost_per_item) }} per item
                  (was {{ formatCurrency(entry.previous_cost_per_item) }}, {{ entry.percent_change }}% better)
                </li>
              </ul>

              <p class="font-semibold text-emerald-700">Unit Cost (Per Gram/ml)</p>
              <p v-if="!receiptResult.insights?.better_unit_cost_items?.length">No unit-cost improvement found.</p>
              <ul v-else class="space-y-2">
                <li
                  v-for="entry in receiptResult.insights.better_unit_cost_items"
                  :key="`better-unit-${entry.name}-${entry.current_cost_per_unit}`"
                  class="rounded-lg bg-white/80 px-2 py-1.5"
                >
                  {{ entry.name }} {{ formatCurrency(entry.current_cost_per_unit) }} {{ entry.unit_label }}
                  (was {{ formatCurrency(entry.previous_cost_per_unit) }}, {{ entry.percent_change }}% better)
                </li>
              </ul>
            </div>
          </article>

          <article class="rounded-xl border border-rose-200 bg-rose-50 p-3">
            <h3 class="text-[11px] font-bold uppercase tracking-wide text-rose-700">Worse Than Previous Bill</h3>
            <p
              v-if="!previousReceiptSnapshot"
              class="mt-2 text-xs text-rose-800"
            >
              Upload another bill to compare same-item costs.
            </p>

            <div v-else class="mt-2 space-y-2 text-xs text-rose-800">
              <p class="font-semibold text-rose-700">Per Item Cost</p>
              <p v-if="!receiptResult.insights?.worse_per_item_items?.length">No per-item increase found.</p>
              <ul v-else class="space-y-2">
                <li
                  v-for="entry in receiptResult.insights.worse_per_item_items"
                  :key="`worse-item-${entry.name}-${entry.current_cost_per_item}`"
                  class="rounded-lg bg-white/80 px-2 py-1.5"
                >
                  {{ entry.name }} {{ formatCurrency(entry.current_cost_per_item) }} per item
                  (was {{ formatCurrency(entry.previous_cost_per_item) }}, {{ entry.percent_change }}% worse)
                </li>
              </ul>

              <p class="font-semibold text-rose-700">Unit Cost (Per Gram/ml)</p>
              <p v-if="!receiptResult.insights?.worse_unit_cost_items?.length">No unit-cost increase found.</p>
              <ul v-else class="space-y-2">
                <li
                  v-for="entry in receiptResult.insights.worse_unit_cost_items"
                  :key="`worse-unit-${entry.name}-${entry.current_cost_per_unit}`"
                  class="rounded-lg bg-white/80 px-2 py-1.5"
                >
                  {{ entry.name }} {{ formatCurrency(entry.current_cost_per_unit) }} {{ entry.unit_label }}
                  (was {{ formatCurrency(entry.previous_cost_per_unit) }}, {{ entry.percent_change }}% worse)
                </li>
              </ul>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="text-sm font-bold text-slate-800 mt-2">Recent Activity</h2>

      <div
        v-if="anomalySignals.anomalies.length"
        class="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2"
      >
        <p class="text-[11px] font-bold uppercase tracking-wide text-amber-700">Unusual Activity</p>
        <p class="mt-1 text-xs text-amber-800">
          {{ anomalySignals.anomalies.length }} potential spike{{ anomalySignals.anomalies.length > 1 ? 's' : '' }} detected in recent spending.
        </p>
      </div>
      
      <div
        v-for="tx in visibleTransactions"
        :key="tx.id"
        class="rounded-2xl bg-white p-4 shadow-sm border border-slate-100"
      >
        <div
          class="flex items-center justify-between"
          :class="tx.direction === 'out' ? 'cursor-pointer' : ''"
          @click="openBucketPicker(tx)"
        >
          <div class="flex items-center gap-3">
            <div class="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-slate-50 text-lg border border-slate-100">
              {{ tx.direction === 'in' ? '📈' : '🛒' }}
            </div>
            <div class="flex flex-col">
              <span class="text-sm font-bold text-slate-800">{{ tx.description }}</span>
              <div class="flex items-center gap-2 mt-0.5">
                <span class="text-[10px] text-slate-500">{{ tx.date }}</span>
                <span class="text-[10px] text-slate-300">•</span>
                <span class="text-[10px] font-medium text-slate-500">{{ tx.bucket }}</span>
                <span
                  v-if="tx.anomaly"
                  class="rounded-full bg-amber-100 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-amber-700"
                >
                  Spike
                </span>
                <span
                  v-if="tx.recurring"
                  class="rounded-full bg-cyan-100 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-cyan-700"
                >
                  {{ tx.recurring.subscription ? 'Subscription' : 'Recurring' }}
                </span>
              </div>
            </div>
          </div>
          <div class="text-right flex flex-col items-end">
            <span class="text-sm font-bold" :class="tx.direction === 'in' ? 'text-emerald-600' : 'text-slate-800'">
              {{ tx.direction === 'in' ? '+' : '-' }}{{ formatCurrency(tx.amount) }}
            </span>
            <span class="text-[10px] font-medium text-slate-400 mt-0.5">{{ tx.category }}</span>
          </div>
        </div>

        <div v-if="selectedTransactionId === tx.id && tx.direction === 'out'" class="mt-3 rounded-xl border border-cyan-100 bg-cyan-50/60 p-3">
          <p class="text-[11px] font-semibold text-slate-700">Move this transaction to bucket:</p>
          <div class="mt-2 flex flex-wrap gap-2">
            <button
              v-for="bucket in editableBucketNames"
              :key="`${tx.id}-${bucket}`"
              type="button"
              class="rounded-full border px-3 py-1 text-[11px] font-semibold transition-colors"
              :class="tx.bucket === bucket ? 'border-cyan-600 bg-cyan-600 text-white' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'"
              @click="saveBucketForTransaction(bucket)"
            >
              {{ bucket }}
            </button>
            <button
              type="button"
              class="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-500 hover:bg-slate-50"
              @click="selectedTransactionId = null"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
      
      <div v-if="!visibleTransactions.length" class="py-8 text-center text-sm text-slate-500">
        No transactions found.
      </div>
    </section>
  </main>
</template>
