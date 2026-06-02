import { computed, ref, watch } from 'vue'
import resolveBackendBaseUrl from '../utils/backendUrl'

const profiles = {
  student: {
    label: 'Student',
    budgetRatio: 0.65,
    emergencyTargetMonths: 2,
    focus: 'Keep fixed costs low and preserve tuition runway.',
    bucketTemplate: {
      Food: 0.18,
      Utilities: 0.1,
      Housing: 0.34,
      Transport: 0.08,
      Health: 0.06,
      Misc: 0.1,
      Savings: 0.14,
    },
  },
  professional: {
    label: 'Professional',
    budgetRatio: 0.72,
    emergencyTargetMonths: 4,
    focus: 'Balance comfort spending with steady long-term savings.',
    bucketTemplate: {
      Food: 0.15,
      Utilities: 0.09,
      Housing: 0.32,
      Transport: 0.1,
      Health: 0.08,
      Misc: 0.1,
      Savings: 0.16,
    },
  },
  advisor: {
    label: 'Advisor',
    budgetRatio: 0.68,
    emergencyTargetMonths: 6,
    focus: 'Track risk-adjusted cash behavior and optimize reserves.',
    bucketTemplate: {
      Food: 0.14,
      Utilities: 0.1,
      Housing: 0.3,
      Transport: 0.08,
      Health: 0.08,
      Misc: 0.1,
      Savings: 0.2,
    },
  },
}

const selectedProfile = ref('professional')

const AUTH_USERS_STORAGE_KEY = 'finance:auth-users'
const AUTH_CURRENT_USER_STORAGE_KEY = 'finance:auth-current-user-id'

const users = ref([])
const currentUser = ref(null)

const normalizeEmail = (value) => String(value ?? '').trim().toLowerCase()

const HARDCODED_AUTH_EMAIL = 'jeswinsunsi@gmail.com'
const HARDCODED_AUTH_PASSWORD = 'readingclub'
const HARDCODED_AUTH_USER = {
  id: 'user-hardcoded-jeswinsunsi',
  firstName: 'Jeswin',
  lastName: 'Sunsi',
  email: HARDCODED_AUTH_EMAIL,
  phone: '',
  password: HARDCODED_AUTH_PASSWORD,
  accounts: [
    {
      id: 'account-hardcoded-jeswinsunsi-primary',
      nickname: 'Primary Account',
      last4: '1001',
      isPrimary: true,
    },
  ],
  createdAt: '2026-03-19T00:00:00.000Z',
}

const createAccountId = () => `account-${Date.now()}-${Math.floor(Math.random() * 100000)}`

const normalizeAccountEntry = (account, index = 0) => {
  const last4 = String(account?.last4 ?? '').replace(/\D/g, '').slice(-4)
  return {
    id: String(account?.id ?? createAccountId()),
    nickname: String(account?.nickname ?? `Account ${index + 1}`).trim() || `Account ${index + 1}`,
    last4,
    isPrimary: Boolean(account?.isPrimary),
  }
}

const ensurePrimaryAccount = (accounts) => {
  if (!Array.isArray(accounts) || accounts.length === 0) {
    return []
  }

  const cloned = accounts.map((account, index) => normalizeAccountEntry(account, index))
  const primary = cloned.find((account) => account.isPrimary)

  if (!primary) {
    cloned[0].isPrimary = true
    return cloned
  }

  return cloned.map((account) => ({
    ...account,
    isPrimary: account.id === primary.id,
  }))
}

const publicUser = (userRecord) => {
  if (!userRecord) {
    return null
  }

  return {
    id: userRecord.id,
    firstName: userRecord.firstName,
    lastName: userRecord.lastName,
    fullName: `${userRecord.firstName} ${userRecord.lastName}`.trim(),
    email: userRecord.email,
    phone: userRecord.phone,
    accounts: ensurePrimaryAccount(userRecord.accounts),
    createdAt: userRecord.createdAt,
  }
}

const withHardcodedAccount = (records) => {
  const normalizedRecords = Array.isArray(records) ? records : []
  const hardcodedEmail = normalizeEmail(HARDCODED_AUTH_EMAIL)
  const matchIndex = normalizedRecords.findIndex(
    (record) => normalizeEmail(record.email) === hardcodedEmail,
  )

  if (matchIndex < 0) {
    return [
      ...normalizedRecords,
      {
        ...HARDCODED_AUTH_USER,
        email: hardcodedEmail,
        accounts: ensurePrimaryAccount(HARDCODED_AUTH_USER.accounts),
      },
    ]
  }

  return normalizedRecords.map((record, index) => {
    if (index !== matchIndex) {
      return record
    }

    return {
      ...record,
      id: HARDCODED_AUTH_USER.id,
      firstName: HARDCODED_AUTH_USER.firstName,
      lastName: HARDCODED_AUTH_USER.lastName,
      email: hardcodedEmail,
      password: HARDCODED_AUTH_PASSWORD,
      accounts: ensurePrimaryAccount(
        Array.isArray(record.accounts) && record.accounts.length > 0
          ? record.accounts
          : HARDCODED_AUTH_USER.accounts,
      ),
      createdAt: record.createdAt ?? HARDCODED_AUTH_USER.createdAt,
    }
  })
}

const persistUsers = () => {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(AUTH_USERS_STORAGE_KEY, JSON.stringify(users.value))
}

const persistCurrentUser = () => {
  if (typeof window === 'undefined') {
    return
  }

  if (!currentUser.value?.id) {
    window.localStorage.removeItem(AUTH_CURRENT_USER_STORAGE_KEY)
    return
  }

  window.localStorage.setItem(AUTH_CURRENT_USER_STORAGE_KEY, currentUser.value.id)
}

const hydrateAuthState = () => {
  if (typeof window === 'undefined') {
    return
  }

  try {
    const rawUsers = window.localStorage.getItem(AUTH_USERS_STORAGE_KEY)
    const parsedUsers = rawUsers ? JSON.parse(rawUsers) : []
    users.value = withHardcodedAccount(
      Array.isArray(parsedUsers)
        ? parsedUsers.map((record) => ({
            ...record,
            email: normalizeEmail(record.email),
            accounts: ensurePrimaryAccount(record.accounts ?? []),
          }))
        : [],
    )
  } catch {
    users.value = withHardcodedAccount([])
  }

  try {
    const currentUserId = window.localStorage.getItem(AUTH_CURRENT_USER_STORAGE_KEY)
    const foundUser = users.value.find((record) => record.id === currentUserId)
    currentUser.value = publicUser(foundUser)
  } catch {
    currentUser.value = null
  }

  persistUsers()
}

const isAuthenticated = computed(() => Boolean(currentUser.value?.id))

const registerUser = ({
  firstName,
  lastName,
  email,
  phone,
  password,
  confirmPassword,
  accounts,
}) => {
  const safeFirstName = String(firstName ?? '').trim()
  const safeLastName = String(lastName ?? '').trim()
  const safeEmail = normalizeEmail(email)
  const safePhone = String(phone ?? '').trim()
  const safePassword = String(password ?? '')
  const safeConfirmPassword = String(confirmPassword ?? '')

  if (!safeFirstName || !safeLastName) {
    return { ok: false, error: 'Please provide your first and last name.' }
  }

  if (!safeEmail || !/^\S+@\S+\.\S+$/.test(safeEmail)) {
    return { ok: false, error: 'Please provide a valid email address.' }
  }

  if (safePassword.length < 8) {
    return { ok: false, error: 'Password must be at least 8 characters long.' }
  }

  if (safePassword !== safeConfirmPassword) {
    return { ok: false, error: 'Password confirmation does not match.' }
  }

  if (users.value.some((record) => record.email === safeEmail)) {
    return { ok: false, error: 'An account with this email already exists.' }
  }

  const cleanedAccounts = ensurePrimaryAccount(
    Array.isArray(accounts)
      ? accounts
          .map((account, index) => normalizeAccountEntry(account, index))
          .filter((account) => account.last4.length === 4)
      : [],
  )

  if (cleanedAccounts.length === 0) {
    return { ok: false, error: 'Add at least one bank account with a valid last 4 digits.' }
  }

  const userRecord = {
    id: `user-${Date.now()}-${Math.floor(Math.random() * 100000)}`,
    firstName: safeFirstName,
    lastName: safeLastName,
    email: safeEmail,
    phone: safePhone,
    password: safePassword,
    accounts: cleanedAccounts,
    createdAt: new Date().toISOString(),
  }

  users.value = [...users.value, userRecord]
  currentUser.value = publicUser(userRecord)
  persistUsers()
  persistCurrentUser()

  return {
    ok: true,
    user: currentUser.value,
  }
}

const loginUser = ({ email, password }) => {
  const safeEmail = normalizeEmail(email)
  const safePassword = String(password ?? '')

  const match = users.value.find(
    (record) => record.email === safeEmail && record.password === safePassword,
  )

  if (!match) {
    return { ok: false, error: 'Invalid email or password.' }
  }

  currentUser.value = publicUser(match)
  persistCurrentUser()

  return {
    ok: true,
    user: currentUser.value,
  }
}

const logoutUser = () => {
  currentUser.value = null
  persistCurrentUser()
}

const addBankAccountForCurrentUser = ({ nickname, last4, setPrimary = false }) => {
  if (!currentUser.value?.id) {
    return { ok: false, error: 'No signed-in user.' }
  }

  const safeLast4 = String(last4 ?? '').replace(/\D/g, '').slice(-4)
  if (safeLast4.length !== 4) {
    return { ok: false, error: 'Bank account last 4 digits must contain exactly 4 numbers.' }
  }

  const account = {
    id: createAccountId(),
    nickname: String(nickname ?? '').trim() || `Account ${currentUser.value.accounts.length + 1}`,
    last4: safeLast4,
    isPrimary: Boolean(setPrimary),
  }

  const withNew = ensurePrimaryAccount([
    ...currentUser.value.accounts.map((entry) => ({ ...entry, isPrimary: setPrimary ? false : entry.isPrimary })),
    account,
  ])

  const userIndex = users.value.findIndex((record) => record.id === currentUser.value.id)
  if (userIndex < 0) {
    return { ok: false, error: 'Could not update user account list.' }
  }

  users.value[userIndex] = {
    ...users.value[userIndex],
    accounts: withNew,
  }
  currentUser.value = publicUser(users.value[userIndex])
  persistUsers()

  return { ok: true, accounts: withNew }
}

const setPrimaryBankAccount = (accountId) => {
  if (!currentUser.value?.id) {
    return false
  }

  const userIndex = users.value.findIndex((record) => record.id === currentUser.value.id)
  if (userIndex < 0) {
    return false
  }

  const accounts = users.value[userIndex].accounts ?? []
  if (!accounts.some((account) => account.id === accountId)) {
    return false
  }

  users.value[userIndex] = {
    ...users.value[userIndex],
    accounts: ensurePrimaryAccount(
      accounts.map((account) => ({
        ...account,
        isPrimary: account.id === accountId,
      })),
    ),
  }

  currentUser.value = publicUser(users.value[userIndex])
  persistUsers()
  return true
}

hydrateAuthState()

const backendBaseUrl = resolveBackendBaseUrl(import.meta.env.VITE_SMS_BACKEND_BASE_URL)

const realtimeStatus = ref('disconnected')
const realtimeError = ref('')
const backendSimulationRunning = ref(false)
const liveMessageCount = ref(0)
const lastLiveMessageAt = ref('')
const backendHealthStatus = ref('unknown')
const backendHealthError = ref('')
const backendDebugUrl = backendBaseUrl
const demoScenarios = ref([])
const activeDemoScenarioId = ref('')
const demoScenarioLoading = ref(false)
const demoScenarioApplying = ref(false)
const demoScenarioError = ref('')

let feedSocket = null
let reconnectTimer = null
let connectionStarted = false
const WS_CONNECT_TIMEOUT_MS = 5000
const seenLiveIds = new Set()

const transactions = ref([
  { id: 1, date: '2026-01-04', description: 'Payroll Deposit', amount: 5400, direction: 'in' },
  { id: 2, date: '2026-01-06', description: 'Rent Transfer', amount: 1720, direction: 'out' },
  { id: 3, date: '2026-01-08', description: 'Metro Card Reload', amount: 78, direction: 'out' },
  { id: 4, date: '2026-01-10', description: 'Grocery Market', amount: 210, direction: 'out' },
  { id: 5, date: '2026-01-14', description: 'Video Streaming', amount: 16, direction: 'out' },
  { id: 6, date: '2026-02-04', description: 'Payroll Deposit', amount: 5400, direction: 'in' },
  { id: 7, date: '2026-02-07', description: 'Coffee and Lunch', amount: 96, direction: 'out' },
  { id: 8, date: '2026-02-09', description: 'Utilities Electricity', amount: 124, direction: 'out' },
  { id: 9, date: '2026-02-11', description: 'Online Shopping', amount: 340, direction: 'out' },
  { id: 10, date: '2026-02-19', description: 'Freelance Invoice', amount: 850, direction: 'in' },
  { id: 11, date: '2026-03-03', description: 'Payroll Deposit', amount: 5400, direction: 'in' },
  { id: 12, date: '2026-03-05', description: 'Gym Membership', amount: 52, direction: 'out' },
  { id: 13, date: '2026-03-07', description: 'Pharmacy Purchase', amount: 45, direction: 'out' },
  { id: 14, date: '2026-03-10', description: 'Dining and Takeout', amount: 240, direction: 'out' },
  { id: 15, date: '2026-03-14', description: 'Travel Booking', amount: 460, direction: 'out' },
  { id: 16, date: '2026-03-16', description: 'Home Internet Bill', amount: 88, direction: 'out' },
  { id: 17, date: '2026-03-17', description: 'Bookstore', amount: 64, direction: 'out' },
])

const simulationMessages = [
  'Paid Rs 18.50 for coffee at Central Cafe',
  'UPI debit 1290 to FreshMart grocery store',
  'Uber ride charged Rs 24.30',
  'Electricity bill paid 3400',
  'Salary credited 5400',
  'Pharmacy purchase amount 45',
  'Netflix subscription 16.99',
]

const categoryRules = {
  Housing: ['rent', 'mortgage', 'lease', 'apartment'],
  Transport: ['metro', 'fuel', 'transport', 'uber', 'taxi', 'bus'],
  Food: ['grocery', 'lunch', 'coffee', 'dining', 'takeout', 'restaurant'],
  Utilities: ['electricity', 'water', 'internet', 'utility', 'bill'],
  Health: ['pharmacy', 'gym', 'doctor', 'clinic', 'hospital'],
  Lifestyle: ['shopping', 'travel', 'streaming', 'entertainment', 'bookstore'],
}

const defaultBucketByCategory = {
  Housing: 'Housing',
  Transport: 'Transport',
  Food: 'Food',
  Utilities: 'Utilities',
  Health: 'Health',
  Lifestyle: 'Misc',
  Other: 'Misc',
}

const bucketByCategory = ref({ ...defaultBucketByCategory })

const buildBucketSettings = (template) =>
  Object.entries(template).map(([name, ratio], index) => ({
    id: `bucket-${index + 1}`,
    name,
    ratio,
    customLimit: null,
  }))

const bucketSettings = ref(buildBucketSettings(profiles[selectedProfile.value].bucketTemplate))

watch(
  selectedProfile,
  (nextProfile) => {
    bucketSettings.value = buildBucketSettings(profiles[nextProfile].bucketTemplate)
    bucketByCategory.value = { ...defaultBucketByCategory }
  },
  { flush: 'sync' },
)

const backendBucketToCategory = {
  Groceries: 'Food',
  'Food & Dining': 'Food',
  Transport: 'Transport',
  Shopping: 'Lifestyle',
  'Bills & Utilities': 'Utilities',
  Health: 'Health',
  Entertainment: 'Lifestyle',
  Investments: 'Other',
  'Cash Withdrawal': 'Other',
  Miscellaneous: 'Other',
}

const expenseHints = [
  'paid',
  'purchase',
  'debit',
  'charged',
  'spent',
  'upi',
  'bill',
  'subscription',
  'transfer to',
]

const incomeHints = ['credited', 'salary', 'deposit', 'received', 'refund']
const subscriptionKeywords = [
  'subscription',
  'membership',
  'netflix',
  'spotify',
  'prime',
  'gym',
  'internet',
  'icloud',
  'youtube',
  'adobe',
  'office',
]

const formatCurrency = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(value)

const toIsoDate = (tx) => tx.occurredAt?.slice(0, 10) ?? tx.date

const parseTxDate = (tx) => new Date(`${toIsoDate(tx)}T00:00:00`)

const dayDiff = (left, right) => {
  const dayMs = 1000 * 60 * 60 * 24
  return Math.round((right.getTime() - left.getTime()) / dayMs)
}

const normalizeMerchantKey = (description) =>
  description
    .toLowerCase()
    .replace(/\b(?:paid|payment|purchase|transfer|bill|invoice|amount|debit|credit)\b/g, ' ')
    .replace(/[^a-z\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const containsSubscriptionHint = (description) =>
  subscriptionKeywords.some((word) => description.toLowerCase().includes(word))

const categorizeTransaction = (tx) => {
  if (tx.category) {
    return tx.category
  }

  if (tx.direction === 'in') {
    return 'Income'
  }

  const source = tx.description.toLowerCase()

  for (const [category, words] of Object.entries(categoryRules)) {
    if (words.some((word) => source.includes(word))) {
      return category
    }
  }

  return 'Other'
}

const findAmountInText = (text) => {
  const normalized = text.replace(/,/g, '')
  const match = normalized.match(/(?:[$€£₹]|rs\.?|inr)?\s*(\d+(?:\.\d{1,2})?)/i)

  if (!match) {
    return 0
  }

  return Number.parseFloat(match[1])
}

const inferDirectionFromMessage = (text) => {
  const lower = text.toLowerCase()

  if (incomeHints.some((hint) => lower.includes(hint))) {
    return 'in'
  }

  if (expenseHints.some((hint) => lower.includes(hint))) {
    return 'out'
  }

  return 'out'
}

const normalizeMessageDescription = (text) =>
  text
    .replace(/\s+/g, ' ')
    .replace(/\b(?:usd|inr|rs\.?|upi)\b/gi, '')
    .trim()

const nextTransactionId = () =>
  transactions.value.reduce((maxId, tx) => Math.max(maxId, tx.id), 0) + 1

const parseMessagesToTransactions = (rawMessages, options = {}) => {
  const { includeIncome = true } = options
  const lines = Array.isArray(rawMessages)
    ? rawMessages
    : rawMessages
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)

  const baseDate = new Date('2026-03-18')
  let idCursor = nextTransactionId()

  return lines
    .map((line, index) => {
      const amount = findAmountInText(line)
      if (!amount) {
        return null
      }

      const direction = inferDirectionFromMessage(line)
      if (!includeIncome && direction === 'in') {
        return null
      }

      const txDate = new Date(baseDate)
      txDate.setDate(baseDate.getDate() - index)

      return {
        id: idCursor++,
        date: txDate.toISOString().slice(0, 10),
        description: normalizeMessageDescription(line),
        amount,
        direction,
        source: 'message-scan',
      }
    })
    .filter(Boolean)
}

const ingestMessages = (rawMessages, options = {}) => {
  const parsed = parseMessagesToTransactions(rawMessages, options)

  if (parsed.length > 0) {
    transactions.value.push(...parsed)
  }

  return parsed
}

const runExpenseSimulation = () => ingestMessages(simulationMessages, { includeIncome: false })

const toWsCandidate = (value) => {
  try {
    const url = new URL(value)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = '/ws/messages'
    url.search = ''
    return url.toString()
  } catch {
    return ''
  }
}

const backendWsCandidates = () => {
  const candidates = [toWsCandidate(backendBaseUrl)]

  if (typeof window !== 'undefined') {
    const pageProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const pageHost = window.location.hostname || '127.0.0.1'

    candidates.push(`${pageProtocol}//${pageHost}:8010/ws/messages`)

    if (pageHost !== '127.0.0.1' && pageHost !== 'localhost') {
      candidates.push(`${pageProtocol}//127.0.0.1:8010/ws/messages`)
      candidates.push(`${pageProtocol}//localhost:8010/ws/messages`)
    }
  }

  return [...new Set(candidates.filter(Boolean))]
}

const toLiveTransaction = (item) => {
  const fallbackId = `${item.transaction_id ?? ''}-${item.timestamp ?? Date.now()}`
  const id = `live-${item.id ?? fallbackId}`

  return {
    id,
    date: (item.timestamp ?? new Date().toISOString()).slice(0, 10),
    description: item.message ?? `Card spend at ${item.merchant ?? 'merchant'}`,
    amount: Number(item.amount) || 0,
    direction: 'out',
    source: 'backend-live',
    occurredAt: item.timestamp ?? new Date().toISOString(),
    category: backendBucketToCategory[item.bucket] ?? 'Other',
    bucket: bucketByCategory.value[backendBucketToCategory[item.bucket] ?? 'Other'] ?? 'Misc',
    backendBucket: item.bucket ?? 'Miscellaneous',
    merchant: item.merchant ?? '',
    transactionId: item.transaction_id ?? '',
  }
}

const addLiveTransaction = (item) => {
  const tx = toLiveTransaction(item)

  if (seenLiveIds.has(tx.id)) {
    return false
  }

  seenLiveIds.add(tx.id)
  transactions.value.push(tx)
  liveMessageCount.value += 1
  lastLiveMessageAt.value = tx.occurredAt ?? new Date().toISOString()
  return true
}

const ingestHistoryPacket = (items) => {
  const sortedItems = [...items].sort((a, b) =>
    String(a.timestamp ?? '').localeCompare(String(b.timestamp ?? '')),
  )

  for (const item of sortedItems) {
    addLiveTransaction(item)
  }
}

const refreshBackendSimulationStatus = async () => {
  try {
    const response = await fetch(`${backendBaseUrl}/simulation/status`)
    if (!response.ok) {
      throw new Error(`Status HTTP ${response.status}`)
    }

    const payload = await response.json()
    backendSimulationRunning.value = Boolean(payload.running)
  } catch {
    backendSimulationRunning.value = false
  }
}

const checkBackendHealth = async () => {
  backendHealthStatus.value = 'checking'
  backendHealthError.value = ''

  try {
    const response = await fetch(`${backendBaseUrl}/health`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
      },
    })

    if (!response.ok) {
      throw new Error(`Health HTTP ${response.status}`)
    }

    backendHealthStatus.value = 'ok'
  } catch (error) {
    backendHealthStatus.value = 'down'
    backendHealthError.value = error instanceof Error ? error.message : 'Health check failed.'
  }
}

const setBackendSimulationState = async (state) => {
  const response = await fetch(`${backendBaseUrl}/simulation/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state }),
  })

  if (!response.ok) {
    throw new Error(`Control HTTP ${response.status}`)
  }

  const payload = await response.json()
  backendSimulationRunning.value = Boolean(payload.running)
  return payload
}

const normalizeScenarioPayload = (payload) => {
  const rawItems =
    payload?.scenarios ?? payload?.items ?? payload?.data?.scenarios ?? payload?.data ?? []

  const normalized = Array.isArray(rawItems)
    ? rawItems
        .map((item, index) => {
          const id = String(item.id ?? item.scenarioId ?? item.slug ?? index)
          const name = String(item.name ?? item.label ?? `Scenario ${index + 1}`)
          return {
            id,
            name,
            description: String(item.description ?? item.detail ?? ''),
            running: Boolean(item.running ?? item.active ?? false),
          }
        })
        .filter((item) => item.id)
    : []

  const activeIdFromPayload =
    payload?.activeScenarioId ??
    payload?.active_scenario_id ??
    payload?.activeScenario ??
    normalized.find((item) => item.running)?.id ??
    ''

  return {
    scenarios: normalized,
    activeId: String(activeIdFromPayload ?? ''),
  }
}

const refreshDemoScenarios = async () => {
  demoScenarioLoading.value = true
  demoScenarioError.value = ''

  try {
    const response = await fetch(`${backendBaseUrl}/simulation/scenarios`)
    if (!response.ok) {
      throw new Error(`Scenarios HTTP ${response.status}`)
    }

    const payload = await response.json()
    const parsed = normalizeScenarioPayload(payload)

    demoScenarios.value = parsed.scenarios
    activeDemoScenarioId.value = parsed.activeId
  } catch {
    demoScenarios.value = []
    activeDemoScenarioId.value = ''
    demoScenarioError.value = 'Scenario catalog unavailable from backend.'
  } finally {
    demoScenarioLoading.value = false
  }
}

const activateDemoScenario = async (scenarioId) => {
  if (!scenarioId) {
    return null
  }

  demoScenarioApplying.value = true
  demoScenarioError.value = ''

  try {
    const response = await fetch(`${backendBaseUrl}/simulation/scenarios/activate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenarioId }),
    })

    if (!response.ok) {
      throw new Error(`Activate HTTP ${response.status}`)
    }

    const payload = await response.json()
    const parsed = normalizeScenarioPayload(payload)

    if (parsed.scenarios.length > 0) {
      demoScenarios.value = parsed.scenarios
    }

    activeDemoScenarioId.value = parsed.activeId || String(scenarioId)
    return payload
  } catch {
    demoScenarioError.value = 'Could not activate backend scenario.'
    return null
  } finally {
    demoScenarioApplying.value = false
  }
}

const ensureRealtimeConnection = () => {
  if (typeof window === 'undefined' || connectionStarted) {
    return
  }

  connectionStarted = true
  realtimeStatus.value = 'connecting'
  realtimeError.value = ''

  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  refreshBackendSimulationStatus()
  refreshDemoScenarios()
  checkBackendHealth()

  const wsCandidates = backendWsCandidates()

  if (wsCandidates.length === 0) {
    realtimeStatus.value = 'error'
    realtimeError.value = 'No websocket endpoint candidates available.'
    connectionStarted = false
    return
  }

  const connectCandidate = (index) => {
    const wsUrl = wsCandidates[index]

    if (!wsUrl) {
      realtimeStatus.value = 'error'
      realtimeError.value = 'Unable to connect to backend live feed.'
      connectionStarted = false
      reconnectTimer = window.setTimeout(() => {
        ensureRealtimeConnection()
      }, 2000)
      return
    }

    let opened = false
    let failed = false
    let connectTimeout = null

    try {
      feedSocket = new WebSocket(wsUrl)
    } catch {
      connectCandidate(index + 1)
      return
    }

    const failAndTryNext = () => {
      if (failed || opened) {
        return
      }

      failed = true
      if (connectTimeout) {
        window.clearTimeout(connectTimeout)
      }

      try {
        feedSocket?.close()
      } catch {
        // Ignore close failures and continue to next candidate.
      }

      connectCandidate(index + 1)
    }

    connectTimeout = window.setTimeout(() => {
      if (!opened) {
        failAndTryNext()
      }
    }, WS_CONNECT_TIMEOUT_MS)

    feedSocket.onopen = () => {
      opened = true
      if (connectTimeout) {
        window.clearTimeout(connectTimeout)
      }

      realtimeStatus.value = 'connected'
      realtimeError.value = ''
    }

    feedSocket.onmessage = (event) => {
      try {
        const packet = JSON.parse(event.data)

        if (packet.type === 'history' && Array.isArray(packet.messages)) {
          ingestHistoryPacket(packet.messages)
          return
        }

        if (packet.type === 'message' && packet.data) {
          addLiveTransaction(packet.data)
        }
      } catch {
        realtimeError.value = 'Live feed packet parse failed.'
      }
    }

    feedSocket.onerror = () => {
      if (!opened) {
        failAndTryNext()
        return
      }

      realtimeStatus.value = 'error'
      realtimeError.value = `Live feed error on ${wsUrl}.`
    }

    feedSocket.onclose = () => {
      if (!opened) {
        failAndTryNext()
        return
      }

      realtimeStatus.value = 'disconnected'
      connectionStarted = false
      reconnectTimer = window.setTimeout(() => {
        ensureRealtimeConnection()
      }, 2000)
    }
  }

  connectCandidate(0)
}

const profile = computed(() => profiles[selectedProfile.value])

const editableBucketNames = computed(() => bucketSettings.value.map((bucket) => bucket.name))

const assignTransactionBucket = (transactionId, bucketName) => {
  if (!editableBucketNames.value.includes(bucketName)) {
    return false
  }

  const tx = transactions.value.find((item) => item.id === transactionId)
  if (!tx || tx.direction !== 'out') {
    return false
  }

  tx.bucket = bucketName
  return true
}

const updateBucketSettings = (bucketId, payload) => {
  const bucket = bucketSettings.value.find((item) => item.id === bucketId)
  if (!bucket) {
    return { ok: false, error: 'Bucket not found.' }
  }

  const nextName = typeof payload.name === 'string' ? payload.name.trim() : bucket.name
  if (!nextName) {
    return { ok: false, error: 'Bucket name is required.' }
  }

  if (
    bucketSettings.value.some(
      (item) => item.id !== bucketId && item.name.toLowerCase() === nextName.toLowerCase(),
    )
  ) {
    return { ok: false, error: 'Bucket name already exists.' }
  }

  const oldName = bucket.name
  if (nextName !== oldName) {
    bucket.name = nextName

    for (const tx of transactions.value) {
      if (tx.direction === 'out' && tx.bucket === oldName) {
        tx.bucket = nextName
      }
    }

    for (const [category, mappedName] of Object.entries(bucketByCategory.value)) {
      if (mappedName === oldName) {
        bucketByCategory.value[category] = nextName
      }
    }
  }

  if (payload.limit !== undefined) {
    const parsedLimit = Number(payload.limit)
    if (!Number.isFinite(parsedLimit) || parsedLimit < 0) {
      return { ok: false, error: 'Budget limit must be a valid positive number.' }
    }
    bucket.customLimit = parsedLimit
  }

  return { ok: true, bucket }
}

const resetBucketLimit = (bucketId) => {
  const bucket = bucketSettings.value.find((item) => item.id === bucketId)
  if (!bucket) {
    return false
  }

  bucket.customLimit = null
  return true
}

const profiledTransactions = computed(() =>
  transactions.value.map((tx) => {
    if (tx.direction === 'in') {
      return {
        ...tx,
        category: tx.category ?? 'Income',
        bucket: tx.bucket ?? 'Income',
      }
    }

    if (tx.category && tx.bucket) {
      return tx
    }

    const category = categorizeTransaction(tx)
    return {
      ...tx,
      category,
      bucket: tx.bucket ?? bucketByCategory.value[category] ?? 'Misc',
    }
  }),
)

const totalIncome = computed(() =>
  profiledTransactions.value
    .filter((tx) => tx.direction === 'in')
    .reduce((sum, tx) => sum + tx.amount, 0),
)

const totalExpenses = computed(() =>
  profiledTransactions.value
    .filter((tx) => tx.direction === 'out')
    .reduce((sum, tx) => sum + tx.amount, 0),
)

const budgetLimit = computed(() => totalIncome.value * profile.value.budgetRatio)
const netFlow = computed(() => totalIncome.value - totalExpenses.value)
const savingsRate = computed(() => (totalIncome.value > 0 ? (netFlow.value / totalIncome.value) * 100 : 0))
const budgetUsedPercent = computed(() =>
  budgetLimit.value > 0 ? Math.min((totalExpenses.value / budgetLimit.value) * 100, 100) : 0,
)

const monthlyTrend = computed(() => {
  const map = new Map()

  for (const tx of profiledTransactions.value) {
    const monthKey = tx.date.slice(0, 7)
    const monthLabel = new Date(`${monthKey}-01`).toLocaleDateString('en-US', { month: 'short' })
    const bucket = map.get(monthKey) ?? { label: monthLabel, income: 0, expenses: 0 }

    if (tx.direction === 'in') bucket.income += tx.amount
    else bucket.expenses += tx.amount

    map.set(monthKey, bucket)
  }

  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([monthKey, value]) => ({
      monthKey,
      ...value,
    }))
})

const currentMonthSummary = computed(() => {
  const datedTransactions = profiledTransactions.value
    .map((tx) => ({ ...tx, isoDate: toIsoDate(tx) }))
    .filter((tx) => /^\d{4}-\d{2}-\d{2}$/.test(tx.isoDate))

  if (!datedTransactions.length) {
    return {
      monthLabel: 'N/A',
      daysInMonth: 30,
      daysElapsed: 1,
      monthIncome: 0,
      monthExpenses: 0,
      monthBudget: 0,
    }
  }

  const latestIsoDate = datedTransactions
    .map((tx) => tx.isoDate)
    .sort((a, b) => a.localeCompare(b))
    .at(-1)
  const activeMonthKey = latestIsoDate.slice(0, 7)
  const monthDate = new Date(`${activeMonthKey}-01T00:00:00`)
  const daysInMonth = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0).getDate()
  const daysElapsed = Math.max(Number(latestIsoDate.slice(8, 10)), 1)

  const monthItems = datedTransactions.filter((tx) => tx.isoDate.startsWith(activeMonthKey))

  const monthIncome = monthItems
    .filter((tx) => tx.direction === 'in')
    .reduce((sum, tx) => sum + tx.amount, 0)

  const monthExpenses = monthItems
    .filter((tx) => tx.direction === 'out')
    .reduce((sum, tx) => sum + tx.amount, 0)

  return {
    monthLabel: monthDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
    daysInMonth,
    daysElapsed,
    monthIncome,
    monthExpenses,
    monthBudget: monthIncome * profile.value.budgetRatio,
  }
})

const monthEndForecast = computed(() => {
  const summary = currentMonthSummary.value
  const projectedExpenses =
    summary.daysElapsed > 0 ? (summary.monthExpenses / summary.daysElapsed) * summary.daysInMonth : 0
  const delta = summary.monthBudget - projectedExpenses

  return {
    ...summary,
    projectedExpenses,
    projectedDailySpend:
      summary.daysElapsed > 0 ? summary.monthExpenses / summary.daysElapsed : summary.monthExpenses,
    budgetDelta: delta,
    status: projectedExpenses <= summary.monthBudget ? 'on-track' : 'at-risk',
    riskPercent:
      summary.monthBudget > 0 ? Math.max((projectedExpenses / summary.monthBudget) * 100 - 100, 0) : 0,
  }
})

const addMonths = (monthKey, offset) => {
  const [yearText, monthText] = String(monthKey).split('-')
  const baseYear = Number.parseInt(yearText, 10)
  const baseMonth = Number.parseInt(monthText, 10)

  if (!Number.isFinite(baseYear) || !Number.isFinite(baseMonth)) {
    return monthKey
  }

  const date = new Date(baseYear, baseMonth - 1 + offset, 1)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  return `${year}-${month}`
}

const spendForecast = computed(() => {
  const monthlyExpenses = monthlyTrend.value
    .map((item, index) => ({
      index,
      label: item.label,
      value: item.expenses,
      monthKey: item.monthKey,
    }))
    .filter((item) => Number.isFinite(item.value) && item.value >= 0)

  if (monthlyExpenses.length === 0) {
    return {
      predictedNextMonth: 0,
      confidence: 0,
      model: '',
      series: [],
      chartPoints: [],
      forecastLabel: 'Next Month',
      upperBound: 0,
      lowerBound: 0,
    }
  }

  const latestMonth = profiledTransactions.value
    .map((tx) => toIsoDate(tx))
    .filter((value) => /^\d{4}-\d{2}-\d{2}$/.test(value))
    .sort((a, b) => a.localeCompare(b))
    .at(-1)
    ?.slice(0, 7)

  const history = (() => {
    if (!latestMonth) {
      return monthlyExpenses
    }

    return monthlyExpenses.map((entry, offset) => ({
      ...entry,
      monthKey: addMonths(latestMonth, -(monthlyExpenses.length - 1 - offset)),
    }))
  })()

  const n = history.length
  const xMean = history.reduce((sum, point) => sum + point.index, 0) / n
  const yMean = history.reduce((sum, point) => sum + point.value, 0) / n

  const varianceX = history.reduce((sum, point) => {
    const centered = point.index - xMean
    return sum + centered * centered
  }, 0)

  const covarianceXY = history.reduce((sum, point) => {
    return sum + (point.index - xMean) * (point.value - yMean)
  }, 0)

  const slope = varianceX > 0 ? covarianceXY / varianceX : 0
  const intercept = yMean - slope * xMean
  const trendPrediction = intercept + slope * n

  const alpha = 0.42
  const smoothed = history.reduce(
    (state, point) => alpha * point.value + (1 - alpha) * state,
    history[0]?.value ?? 0,
  )

  const rawPrediction = trendPrediction * 0.6 + smoothed * 0.4
  const predictedNextMonth = Math.max(rawPrediction, 0)

  const residualVariance =
    n > 1
      ? history.reduce((sum, point) => {
          const estimate = intercept + slope * point.index
          const residual = point.value - estimate
          return sum + residual * residual
        }, 0) / (n - 1)
      : 0
  const residualStd = Math.sqrt(residualVariance)

  const coefficientOfVariation = yMean > 0 ? residualStd / yMean : 1
  const confidenceBase = Math.min(n / 6, 1)
  const confidence = Math.max(Math.min((1 - coefficientOfVariation) * confidenceBase, 0.97), 0.25)

  const boundPadding = residualStd * 1.2 + predictedNextMonth * 0.06
  const lowerBound = Math.max(predictedNextMonth - boundPadding, 0)
  const upperBound = predictedNextMonth + boundPadding

  const forecastMonthKey = latestMonth ? addMonths(latestMonth, 1) : 'Next'
  const forecastDate = /^\d{4}-\d{2}$/.test(forecastMonthKey)
    ? new Date(`${forecastMonthKey}-01T00:00:00`)
    : null
  const forecastLabel = forecastDate
    ? forecastDate.toLocaleDateString('en-US', { month: 'short' })
    : 'Next'

  const series = history.map((point) => ({
    label: point.label,
    monthKey: point.monthKey,
    value: point.value,
    isForecast: false,
  }))

  const chartPoints = [
    ...series,
    {
      label: forecastLabel,
      monthKey: forecastMonthKey,
      value: predictedNextMonth,
      isForecast: true,
    },
  ]

  return {
    predictedNextMonth,
    confidence,
    model: '',
    series,
    chartPoints,
    forecastLabel,
    lowerBound,
    upperBound,
  }
})

const anomalySignals = computed(() => {
  const spendingItems = profiledTransactions.value
    .filter((tx) => tx.direction === 'out')
    .slice()
    .sort((a, b) => parseTxDate(a).getTime() - parseTxDate(b).getTime())

  const merchantStats = new Map()
  const categoryStats = new Map()
  const byId = {}
  const anomalies = []

  for (const tx of spendingItems) {
    const merchantKey = normalizeMerchantKey(tx.description) || tx.category.toLowerCase()
    const merchant = merchantStats.get(merchantKey) ?? { count: 0, sum: 0, sumSq: 0 }
    const category = categoryStats.get(tx.category) ?? { count: 0, sum: 0, sumSq: 0 }

    const merchantMean = merchant.count > 0 ? merchant.sum / merchant.count : tx.amount
    const merchantVariance =
      merchant.count > 1
        ? Math.max(merchant.sumSq / merchant.count - merchantMean * merchantMean, 0)
        : 0
    const merchantStd = Math.sqrt(merchantVariance)
    const merchantSpike =
      merchant.count >= 2 &&
      tx.amount >= 75 &&
      tx.amount > Math.max(merchantMean * 1.85, merchantMean + merchantStd * 2.5)

    const categoryMean = category.count > 0 ? category.sum / category.count : tx.amount
    const categoryVariance =
      category.count > 1
        ? Math.max(category.sumSq / category.count - categoryMean * categoryMean, 0)
        : 0
    const categoryStd = Math.sqrt(categoryVariance)
    const categorySpike =
      category.count >= 4 &&
      tx.amount >= 100 &&
      tx.amount > Math.max(categoryMean * 2.1, categoryMean + categoryStd * 2.8)

    if (merchantSpike || categorySpike) {
      const baseline = merchant.count >= 2 ? merchantMean : categoryMean
      const ratio = baseline > 0 ? tx.amount / baseline : 1
      const severity = ratio >= 2.6 ? 'high' : ratio >= 2 ? 'medium' : 'low'

      const anomaly = {
        id: tx.id,
        description: tx.description,
        date: toIsoDate(tx),
        amount: tx.amount,
        category: tx.category,
        reason: merchantSpike ? 'merchant-spike' : 'category-spike',
        severity,
        ratio,
        baseline,
      }

      anomalies.push(anomaly)
      byId[tx.id] = anomaly
    }

    merchantStats.set(merchantKey, {
      count: merchant.count + 1,
      sum: merchant.sum + tx.amount,
      sumSq: merchant.sumSq + tx.amount * tx.amount,
    })

    categoryStats.set(tx.category, {
      count: category.count + 1,
      sum: category.sum + tx.amount,
      sumSq: category.sumSq + tx.amount * tx.amount,
    })
  }

  return {
    byId,
    anomalies: anomalies.sort((a, b) => b.date.localeCompare(a.date)),
  }
})

const recurringSignals = computed(() => {
  const groups = new Map()

  for (const tx of profiledTransactions.value) {
    if (tx.direction !== 'out') {
      continue
    }

    const key = normalizeMerchantKey(tx.description)
    if (!key) {
      continue
    }

    const next = groups.get(key) ?? []
    next.push(tx)
    groups.set(key, next)
  }

  const byId = {}
  const recurring = []

  for (const [merchantKey, items] of groups.entries()) {
    if (items.length < 2) {
      continue
    }

    const sorted = items.slice().sort((a, b) => parseTxDate(a).getTime() - parseTxDate(b).getTime())
    const gaps = []
    for (let index = 1; index < sorted.length; index += 1) {
      gaps.push(dayDiff(parseTxDate(sorted[index - 1]), parseTxDate(sorted[index])))
    }

    const avgGap = gaps.length > 0 ? gaps.reduce((sum, value) => sum + value, 0) / gaps.length : 0
    const avgAmount = sorted.reduce((sum, tx) => sum + tx.amount, 0) / sorted.length
    const amountRange =
      Math.max(...sorted.map((tx) => tx.amount)) - Math.min(...sorted.map((tx) => tx.amount))
    const stableAmount = avgAmount > 0 ? amountRange / avgAmount < 0.35 : false

    const cadence = avgGap >= 25 && avgGap <= 35 ? 'monthly' : avgGap >= 6 && avgGap <= 8 ? 'weekly' : ''
    const subscription = sorted.some((tx) => containsSubscriptionHint(tx.description))
    const recurringMatch = Boolean(cadence) && (stableAmount || subscription)

    if (!recurringMatch) {
      continue
    }

    const last = sorted.at(-1)
    const nextDate = new Date(parseTxDate(last))
    nextDate.setDate(nextDate.getDate() + Math.max(Math.round(avgGap), 1))

    const signal = {
      id: merchantKey,
      merchant: last.description,
      cadence,
      subscription,
      predictedAmount: avgAmount,
      nextExpectedDate: nextDate.toISOString().slice(0, 10),
      transactionIds: sorted.map((tx) => tx.id),
    }

    recurring.push(signal)

    for (const tx of sorted) {
      byId[tx.id] = {
        cadence,
        subscription,
      }
    }
  }

  return {
    byId,
    recurring: recurring.sort((a, b) => b.predictedAmount - a.predictedAmount),
  }
})

const profiledTransactionsWithSignals = computed(() =>
  profiledTransactions.value.map((tx) => ({
    ...tx,
    anomaly: anomalySignals.value.byId[tx.id] ?? null,
    recurring: recurringSignals.value.byId[tx.id] ?? null,
  })),
)

const maxTrendValue = computed(() =>
  Math.max(...monthlyTrend.value.map((item) => Math.max(item.income, item.expenses)), 1),
)

const categorySummary = computed(() => {
  const grouped = {}

  for (const tx of profiledTransactions.value.filter((item) => item.direction === 'out')) {
    grouped[tx.category] = (grouped[tx.category] ?? 0) + tx.amount
  }

  return Object.entries(grouped)
    .map(([name, amount]) => ({
      name,
      amount,
      percent: totalExpenses.value > 0 ? (amount / totalExpenses.value) * 100 : 0,
    }))
    .sort((a, b) => b.amount - a.amount)
})

const bucketAllocation = computed(() => {
  return bucketSettings.value.map((bucket) => {
    const allocated = bucket.customLimit ?? totalIncome.value * bucket.ratio
    const spent = profiledTransactions.value
      .filter((tx) => tx.direction === 'out' && tx.bucket === bucket.name)
      .reduce((sum, tx) => sum + tx.amount, 0)

    return {
      id: bucket.id,
      name: bucket.name,
      ratio: bucket.ratio,
      customLimit: bucket.customLimit,
      allocated,
      spent,
      remaining: allocated - spent,
      utilization: allocated > 0 ? (spent / allocated) * 100 : 0,
    }
  })
})

const emergencyFundMonths = computed(() => {
  const monthlyBase = Math.max(totalExpenses.value / 3, 1)
  return netFlow.value > 0 ? (netFlow.value * 3) / monthlyBase : 0
})

const riskSignals = computed(() => {
  const discretionary = bucketAllocation.value
    .filter((item) => ['Food', 'Misc'].includes(item.name))
    .reduce((sum, item) => sum + item.spent, 0)

  return {
    overspending: totalExpenses.value > budgetLimit.value,
    discretionarySpike: totalExpenses.value > 0 ? discretionary / totalExpenses.value > 0.4 : false,
    weakReserve: emergencyFundMonths.value < profile.value.emergencyTargetMonths,
    bucketPressure: bucketAllocation.value.some((item) => item.utilization > 100),
  }
})

const toasts = ref([])
let toastIdCursor = 0

const pushToast = (message, severity = 'info') => {
  const id = ++toastIdCursor
  toasts.value.push({ id, message, severity })

  window.setTimeout(() => {
    toasts.value = toasts.value.filter((toast) => toast.id !== id)
  }, 7500)

  return id
}

const dismissToast = (toastId) => {
  toasts.value = toasts.value.filter((toast) => toast.id !== toastId)
}

watch(
  riskSignals,
  (next, prev) => {
    if (next.overspending && !prev?.overspending) {
      pushToast('Severe: Total spending crossed your budget.', 'severe')
    }

    if (next.bucketPressure && !prev?.bucketPressure) {
      pushToast('Severe: A bucket is now overspent.', 'severe')
    }
  },
  { immediate: true },
)

const financialHealthScore = computed(() => {
  let score = 90

  if (riskSignals.value.overspending) score -= 25
  if (riskSignals.value.discretionarySpike) score -= 12
  if (riskSignals.value.weakReserve) score -= 18
  if (riskSignals.value.bucketPressure) score -= 10
  if (savingsRate.value >= 20) score += 6

  return Math.min(Math.max(score, 30), 99)
})

const recommendations = computed(() => {
  const notes = []

  if (monthEndForecast.value.status === 'at-risk') {
    notes.push({
      title: 'Month-end burn rate is at risk',
      priority: 'High',
      detail: `Projected spend is ${formatCurrency(monthEndForecast.value.projectedExpenses)} against a budget of ${formatCurrency(monthEndForecast.value.monthBudget)}. Slow variable expenses now.`,
    })
  }

  if (riskSignals.value.bucketPressure) {
    notes.push({
      title: 'Rebalance bucket allocations',
      priority: 'High',
      detail: 'One or more spending buckets are over capacity. Shift discretionary spend to stay inside each envelope.',
    })
  }

  if (riskSignals.value.overspending) {
    notes.push({
      title: 'Enforce budget guardrail',
      priority: 'High',
      detail: `Expenses exceed budget by ${formatCurrency(totalExpenses.value - budgetLimit.value)}. Freeze optional purchases for the next 10 days.`,
    })
  }

  if (riskSignals.value.weakReserve) {
    notes.push({
      title: 'Increase emergency reserve pace',
      priority: 'Medium',
      detail: `Current reserve runway is ${emergencyFundMonths.value.toFixed(1)} months. Target ${profile.value.emergencyTargetMonths} months with scheduled transfers.`,
    })
  }

  if (anomalySignals.value.anomalies.length > 0) {
    const topAnomaly = anomalySignals.value.anomalies[0]
    notes.push({
      title: 'Unusual spending spike detected',
      priority: topAnomaly.severity === 'high' ? 'High' : 'Medium',
      detail: `${topAnomaly.description} at ${formatCurrency(topAnomaly.amount)} is above your normal spend pattern. Confirm this charge and review merchant controls.`,
    })
  }

  if (recurringSignals.value.recurring.length > 0) {
    notes.push({
      title: 'Recurring charges identified',
      priority: 'Medium',
      detail: `${recurringSignals.value.recurring.length} recurring merchants were detected. Shift non-essential subscriptions into a capped bucket.`,
    })
  }

  notes.push({
    title: 'Activate auto-segregation transfers',
    priority: 'Low',
    detail: 'Move income into Food, Utilities, Housing, Transport, Health, Misc, and Savings buckets immediately on deposit.',
  })

  return notes
})

const opportunities = computed(() => [
  {
    title: 'Food bucket optimization',
    value: formatCurrency(
      (bucketAllocation.value.find((item) => item.name === 'Food')?.spent ?? 0) * 0.14,
    ),
    detail: 'Reduce meal delivery and subscription snack orders.',
  },
  {
    title: 'Utilities efficiency',
    value: formatCurrency(
      (bucketAllocation.value.find((item) => item.name === 'Utilities')?.spent ?? 0) * 0.1,
    ),
    detail: 'Lower recurring utility bills through usage caps and plan comparisons.',
  },
  {
    title: 'Automatic savings sweep',
    value: formatCurrency(Math.max(netFlow.value * 0.35, 0)),
    detail: 'Daily sweep from checking to savings when balance exceeds threshold.',
  },
])

const benefitPoints = [
  'Encourages responsible habits through automatic bucket limits and alerts.',
  'Improves financial awareness with real-time categorization and spending trend intelligence.',
  'Supports planning with risk scoring, opportunity forecasting, and guided recommendations.',
]

const categoryColor = {
  Housing: 'bg-slate-700',
  Transport: 'bg-cyan-600',
  Food: 'bg-amber-500',
  Utilities: 'bg-blue-600',
  Health: 'bg-emerald-600',
  Lifestyle: 'bg-rose-500',
  Other: 'bg-violet-500',
}

const bucketColor = {
  Food: 'bg-amber-500',
  Utilities: 'bg-blue-600',
  Housing: 'bg-slate-700',
  Transport: 'bg-cyan-600',
  Health: 'bg-emerald-600',
  Misc: 'bg-fuchsia-500',
  Savings: 'bg-lime-600',
}

let realtimeWatcherBound = false

const bindRealtimeWatcher = () => {
  if (realtimeWatcherBound) {
    return
  }

  realtimeWatcherBound = true
  ensureRealtimeConnection()
}

export const useFinanceData = () => {
  bindRealtimeWatcher()

  return {
    users,
    currentUser,
    isAuthenticated,
    registerUser,
    loginUser,
    logoutUser,
    addBankAccountForCurrentUser,
    setPrimaryBankAccount,
    profiles,
    selectedProfile,
    profile,
    transactions,
    simulationMessages,
    profiledTransactions,
    editableBucketNames,
    bucketSettings,
    assignTransactionBucket,
    updateBucketSettings,
    resetBucketLimit,
    totalIncome,
    totalExpenses,
    budgetLimit,
    budgetUsedPercent,
    netFlow,
    savingsRate,
    monthlyTrend,
    maxTrendValue,
    currentMonthSummary,
    monthEndForecast,
    spendForecast,
    anomalySignals,
    recurringSignals,
    profiledTransactionsWithSignals,
    categorySummary,
    bucketAllocation,
    emergencyFundMonths,
    riskSignals,
    financialHealthScore,
    recommendations,
    opportunities,
    benefitPoints,
    categoryColor,
    bucketColor,
    parseMessagesToTransactions,
    ingestMessages,
    runExpenseSimulation,
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
    demoScenarios,
    activeDemoScenarioId,
    demoScenarioLoading,
    demoScenarioApplying,
    demoScenarioError,
    refreshDemoScenarios,
    activateDemoScenario,
    toasts,
    dismissToast,
    formatCurrency,
  }
}

export default useFinanceData
