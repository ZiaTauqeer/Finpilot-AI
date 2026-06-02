<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import useFinanceData from './composables/useFinanceData'

const route = useRoute()
const router = useRouter()
const {
  toasts,
  dismissToast,
  currentUser,
  logoutUser,
  realtimeStatus,
  realtimeError,
  backendSimulationRunning,
  backendDebugUrl,
  backendHealthStatus,
  backendHealthError,
  checkBackendHealth,
  liveMessageCount,
  lastLiveMessageAt,
  refreshBackendSimulationStatus,
  setBackendSimulationState,
} = useFinanceData()

const navItems = [
  { label: 'Dashboard', path: '/', icon: '<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>' },
  { label: 'Transactions', path: '/transactions', icon: '<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>' },
  { label: 'Buckets', path: '/buckets', icon: '<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>' },
  { label: 'Insights', path: '/insights', icon: '<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>' },
]

const isActive = (path) => route.path === path

const toastTitle = (severity) => (severity === 'severe' ? 'Budget Alert' : 'Heads up')

const toastTone = (severity) =>
  severity === 'severe'
    ? 'border-rose-200 bg-rose-50/95 text-rose-800 backdrop-blur-md shadow-lg shadow-rose-900/5'
    : 'border-slate-200 bg-white/95 text-slate-800 backdrop-blur-md shadow-lg shadow-slate-900/5'

const toastIconWrap = (severity) =>
  severity === 'severe'
    ? 'bg-rose-100 text-rose-700 ring-4 ring-rose-50'
    : 'bg-cyan-100 text-cyan-700 ring-4 ring-cyan-50'

const toastIcon = (severity) =>
  severity === 'severe'
    ? '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>'
    : '<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>'

const deferredInstallPrompt = ref(null)
const canInstallPwa = ref(false)
const debugOverlayMinimized = ref(false)
let debugRefreshTimer = null
const showDebugOverlay = String(import.meta.env.VITE_SHOW_DEBUG_OVERLAY ?? '').toLowerCase() === 'true'

const isAuthRoute = computed(() => route.name === 'auth')
const userInitials = computed(() => {
  const first = currentUser.value?.firstName?.[0] ?? ''
  const last = currentUser.value?.lastName?.[0] ?? ''
  return `${first}${last}`.toUpperCase() || 'FP'
})

const displayName = computed(() => currentUser.value?.firstName ?? 'there')
const debugRealtimeTone = computed(() => {
  if (realtimeStatus.value === 'connected') {
    return 'bg-emerald-100 text-emerald-700'
  }

  if (realtimeStatus.value === 'connecting') {
    return 'bg-amber-100 text-amber-700'
  }

  return 'bg-rose-100 text-rose-700'
})

const debugHealthTone = computed(() => {
  if (backendHealthStatus.value === 'ok') {
    return 'bg-emerald-100 text-emerald-700'
  }

  if (backendHealthStatus.value === 'checking') {
    return 'bg-amber-100 text-amber-700'
  }

  return 'bg-rose-100 text-rose-700'
})

const toggleDebugOverlay = () => {
  debugOverlayMinimized.value = !debugOverlayMinimized.value

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(
      'finance:debug-overlay-minimized',
      String(debugOverlayMinimized.value),
    )
  }
}

const debugRefresh = async () => {
  await Promise.allSettled([checkBackendHealth(), refreshBackendSimulationStatus()])
}

const toggleBackendSimulation = async () => {
  const nextState = backendSimulationRunning.value ? 'stop' : 'start'

  try {
    await setBackendSimulationState(nextState)
  } catch {
    await refreshBackendSimulationStatus()
  }
}

const handleLogout = async () => {
  logoutUser()
  await router.push({ name: 'auth' })
}

const onBeforeInstallPrompt = (event) => {
  event.preventDefault()
  deferredInstallPrompt.value = event
  canInstallPwa.value = true
}

const onAppInstalled = () => {
  deferredInstallPrompt.value = null
  canInstallPwa.value = false
}

const promptInstall = async () => {
  if (!deferredInstallPrompt.value) {
    return
  }

  deferredInstallPrompt.value.prompt()
  await deferredInstallPrompt.value.userChoice

  deferredInstallPrompt.value = null
  canInstallPwa.value = false
}

onMounted(() => {
  try {
    const persisted = window.localStorage.getItem('finance:debug-overlay-minimized')
    if (persisted === 'true' || persisted === 'false') {
      debugOverlayMinimized.value = persisted === 'true'
    }
  } catch {
    debugOverlayMinimized.value = false
  }

  window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt)
  window.addEventListener('appinstalled', onAppInstalled)

  debugRefresh()
  debugRefreshTimer = window.setInterval(debugRefresh, 5000)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt)
  window.removeEventListener('appinstalled', onAppInstalled)

  if (debugRefreshTimer) {
    window.clearInterval(debugRefreshTimer)
    debugRefreshTimer = null
  }
})
</script>

<template>
  <div
    class="relative mx-auto min-h-screen w-full max-w-md overflow-hidden bg-slate-50 shadow-2xl sm:border-x sm:border-slate-200"
    :class="isAuthRoute ? 'pb-0' : 'pb-20'"
  >
    <header v-if="!isAuthRoute" class="sticky top-0 z-20 border-b border-slate-200 bg-white/90 px-4 py-4 pt-8 backdrop-blur-md">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="font-display text-xl font-bold tracking-tight text-slate-900">FinPilot</h1>
          <p class="text-xs font-medium text-slate-500">Good Morning, {{ displayName }}</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500 transition hover:bg-slate-100"
            @click="handleLogout"
          >
            Sign out
          </button>
          <div class="grid h-10 w-10 place-items-center rounded-full bg-slate-100 text-slate-600 shadow-sm ring-1 ring-slate-200">
            <span class="text-sm font-bold">{{ userInitials }}</span>
          </div>
        </div>
      </div>
      <button
        v-if="canInstallPwa"
        type="button"
        class="mt-3 inline-flex items-center gap-1 rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-[11px] font-semibold text-cyan-700 transition hover:bg-cyan-100"
        @click="promptInstall"
      >
        Install app
      </button>
    </header>

    <div v-if="!isAuthRoute" class="pointer-events-none fixed left-1/2 top-24 z-40 w-full max-w-md -translate-x-1/2 px-4">
      <TransitionGroup name="toast" tag="div" class="flex flex-col gap-2">
        <article
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto rounded-lg border p-4 shadow-lg"
          :class="toastTone(toast.severity)"
        >
          <div class="flex items-start gap-3">
            <div
              class="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full"
              :class="toastIconWrap(toast.severity)"
              aria-hidden="true"
              v-html="toastIcon(toast.severity)"
            >
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-[10px] font-bold uppercase tracking-wider text-current/70">{{ toastTitle(toast.severity) }}</p>
              <p class="mt-1 text-xs font-medium leading-relaxed text-current">{{ toast.message }}</p>
            </div>
            <button
              type="button"
              class="rounded-full p-1 text-current/50 transition hover:bg-current/10 hover:text-current"
              @click="dismissToast(toast.id)"
              aria-label="Dismiss notification"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </article>
      </TransitionGroup>
    </div>

    <RouterView />

    <div
      v-if="!isAuthRoute && showDebugOverlay"
      class="fixed bottom-24 right-3 z-40 w-[min(22rem,calc(100vw-1.5rem))] rounded-2xl border border-slate-300 bg-slate-900/95 p-3 text-slate-100 shadow-2xl backdrop-blur"
    >
      <div class="flex items-center justify-between gap-2">
        <div>
          <p class="text-[10px] font-bold uppercase tracking-[0.16em] text-cyan-300">Debug Overlay</p>
          <p class="text-[11px] text-slate-300">Realtime + backend sync state</p>
        </div>
        <button
          type="button"
          class="rounded-full border border-slate-600 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-200 transition hover:bg-slate-800"
          @click="toggleDebugOverlay"
        >
          {{ debugOverlayMinimized ? 'Expand' : 'Minimize' }}
        </button>
      </div>

      <div v-if="!debugOverlayMinimized" class="mt-3 space-y-2.5 text-[11px]">
        <div class="flex items-center justify-between rounded-lg bg-slate-800/90 px-2.5 py-2">
          <span class="text-slate-300">Realtime</span>
          <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase" :class="debugRealtimeTone">
            {{ realtimeStatus }}
          </span>
        </div>

        <div class="flex items-center justify-between rounded-lg bg-slate-800/90 px-2.5 py-2">
          <span class="text-slate-300">Backend health</span>
          <span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase" :class="debugHealthTone">
            {{ backendHealthStatus }}
          </span>
        </div>

        <div class="flex items-center justify-between rounded-lg bg-slate-800/90 px-2.5 py-2">
          <span class="text-slate-300">Simulation</span>
          <span
            class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
            :class="backendSimulationRunning ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'"
          >
            {{ backendSimulationRunning ? 'running' : 'stopped' }}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <div class="rounded-lg bg-slate-800/90 px-2.5 py-2">
            <p class="text-[10px] uppercase tracking-wide text-slate-400">Live messages</p>
            <p class="mt-1 text-base font-bold text-cyan-300">{{ liveMessageCount }}</p>
          </div>
          <div class="rounded-lg bg-slate-800/90 px-2.5 py-2">
            <p class="text-[10px] uppercase tracking-wide text-slate-400">Last message</p>
            <p class="mt-1 truncate text-[11px] font-semibold text-slate-200">
              {{ lastLiveMessageAt || 'none yet' }}
            </p>
          </div>
        </div>

        <p class="truncate rounded-lg bg-slate-800/90 px-2.5 py-2 text-[10px] text-slate-300">
          Backend: {{ backendDebugUrl }}
        </p>

        <div v-if="realtimeError || backendHealthError" class="rounded-lg border border-rose-400/50 bg-rose-500/10 px-2.5 py-2 text-[10px] text-rose-100">
          {{ realtimeError || backendHealthError }}
        </div>

        <div class="flex gap-2 pt-1">
          <button
            type="button"
            class="flex-1 rounded-lg border border-slate-600 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-100 transition hover:bg-slate-800"
            @click="debugRefresh"
          >
            Refresh
          </button>
          <button
            type="button"
            class="flex-1 rounded-lg border border-cyan-400/70 bg-cyan-500/20 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-cyan-100 transition hover:bg-cyan-500/30"
            @click="toggleBackendSimulation"
          >
            {{ backendSimulationRunning ? 'Stop Sim' : 'Start Sim' }}
          </button>
        </div>
      </div>
    </div>

    <nav
      v-if="!isAuthRoute"
      class="fixed bottom-0 z-30 flex w-full max-w-md items-center justify-around border-t border-slate-200 bg-white pb-safe pt-2 sm:px-0 px-2 pb-6"
    >
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex w-16 flex-col items-center gap-1 rounded-xl p-2 transition-colors"
        :class="isActive(item.path) ? 'text-cyan-600' : 'text-slate-400 hover:text-slate-600'"
      >
        <span v-html="item.icon" class="mb-0.5"></span>
        <span class="text-[10px] font-semibold tracking-wide">{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 180ms ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.toast-move {
  transition: transform 180ms ease;
}
</style>
