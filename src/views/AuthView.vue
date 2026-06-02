<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import useFinanceData from '../composables/useFinanceData'

const router = useRouter()
const { registerUser, loginUser } = useFinanceData()

const mode = ref('signup')
const formError = ref('')
const formBusy = ref(false)

const buildAccountRow = (index = 0) => ({
  id: `form-account-${Date.now()}-${Math.floor(Math.random() * 100000)}`,
  nickname: index === 0 ? 'Primary' : '',
  last4: '',
  isPrimary: index === 0,
})

const signInForm = reactive({
  email: '',
  password: '',
})

const signUpForm = reactive({
  firstName: '',
  lastName: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
  accounts: [buildAccountRow(0)],
})

const sanitizeLast4Input = (account) => {
  account.last4 = String(account.last4 ?? '')
    .replace(/\D/g, '')
    .slice(0, 4)
}

const setPrimary = (accountId) => {
  signUpForm.accounts = signUpForm.accounts.map((account) => ({
    ...account,
    isPrimary: account.id === accountId,
  }))
}

const addAccount = () => {
  signUpForm.accounts.push(buildAccountRow(signUpForm.accounts.length))
}

const removeAccount = (accountId) => {
  if (signUpForm.accounts.length === 1) {
    return
  }

  const removedPrimary = signUpForm.accounts.find((account) => account.id === accountId)?.isPrimary
  signUpForm.accounts = signUpForm.accounts.filter((account) => account.id !== accountId)

  if (removedPrimary && signUpForm.accounts.length > 0) {
    signUpForm.accounts[0].isPrimary = true
  }
}

const switchMode = (nextMode) => {
  formError.value = ''
  mode.value = nextMode
}

const submitSignIn = async () => {
  formBusy.value = true
  formError.value = ''

  const result = loginUser({
    email: signInForm.email,
    password: signInForm.password,
  })

  formBusy.value = false

  if (!result.ok) {
    formError.value = result.error
    return
  }

  router.push({ name: 'dashboard' })
}

const submitSignUp = async () => {
  formBusy.value = true
  formError.value = ''

  const result = registerUser({
    firstName: signUpForm.firstName,
    lastName: signUpForm.lastName,
    email: signUpForm.email,
    phone: signUpForm.phone,
    password: signUpForm.password,
    confirmPassword: signUpForm.confirmPassword,
    accounts: signUpForm.accounts,
  })

  formBusy.value = false

  if (!result.ok) {
    formError.value = result.error
    return
  }

  router.push({ name: 'dashboard' })
}
</script>

<template>
  <main class="min-h-screen w-full bg-slate-100 px-4 py-8">
    <div class="mx-auto w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-xl">
      <div class="mb-6">
        <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-700">FinPilot</p>
        <h1 class="mt-2 font-display text-3xl font-bold text-slate-900">
          {{ mode === 'signup' ? 'Create your account' : 'Welcome back' }}
        </h1>
        <p class="mt-2 text-sm text-slate-500">
          {{
            mode === 'signup'
              ? 'Set up your profile and add the last 4 digits for each bank account.'
              : 'Sign in to continue to your finance dashboard.'
          }}
        </p>
      </div>

      <div class="mb-6 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
        <button
          type="button"
          class="rounded-lg px-3 py-2 text-sm font-semibold transition"
          :class="mode === 'signup' ? 'bg-white text-slate-900 shadow' : 'text-slate-500 hover:text-slate-700'"
          @click="switchMode('signup')"
        >
          Sign Up
        </button>
        <button
          type="button"
          class="rounded-lg px-3 py-2 text-sm font-semibold transition"
          :class="mode === 'signin' ? 'bg-white text-slate-900 shadow' : 'text-slate-500 hover:text-slate-700'"
          @click="switchMode('signin')"
        >
          Sign In
        </button>
      </div>

      <form v-if="mode === 'signup'" class="space-y-4" @submit.prevent="submitSignUp">
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-xs font-semibold text-slate-600">
            First name
            <input
              v-model="signUpForm.firstName"
              type="text"
              required
              autocomplete="given-name"
              class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none ring-cyan-200 transition focus:ring"
            />
          </label>
          <label class="block text-xs font-semibold text-slate-600">
            Last name
            <input
              v-model="signUpForm.lastName"
              type="text"
              required
              autocomplete="family-name"
              class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none ring-cyan-200 transition focus:ring"
            />
          </label>
        </div>

        <label class="block text-xs font-semibold text-slate-600">
          Email
          <input
            v-model="signUpForm.email"
            type="email"
            required
            autocomplete="email"
            class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none ring-cyan-200 transition focus:ring"
          />
        </label>

        <label class="block text-xs font-semibold text-slate-600">
          Phone number
          <input
            v-model="signUpForm.phone"
            type="tel"
            autocomplete="tel"
            class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none ring-cyan-200 transition focus:ring"
          />
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="block text-xs font-semibold text-slate-600">
            Password
            <input
              v-model="signUpForm.password"
              type="password"
              required
              autocomplete="new-password"
              class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none ring-cyan-200 transition focus:ring"
            />
          </label>
          <label class="block text-xs font-semibold text-slate-600">
            Confirm password
            <input
              v-model="signUpForm.confirmPassword"
              type="password"
              required
              autocomplete="new-password"
              class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none ring-cyan-200 transition focus:ring"
            />
          </label>
        </div>

        <section class="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div class="mb-3 flex items-center justify-between gap-3">
            <h2 class="text-sm font-bold text-slate-800">Bank Accounts</h2>
            <button
              type="button"
              class="rounded-lg border border-cyan-200 bg-cyan-50 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-cyan-700"
              @click="addAccount"
            >
              Add account
            </button>
          </div>

          <div class="space-y-3">
            <article
              v-for="(account, index) in signUpForm.accounts"
              :key="account.id"
              class="rounded-xl border border-slate-200 bg-white p-3"
            >
              <div class="grid grid-cols-[1fr_auto] gap-2">
                <label class="block text-xs font-semibold text-slate-600">
                  Account label
                  <input
                    v-model="account.nickname"
                    type="text"
                    placeholder="Checking, Savings"
                    class="mt-1 w-full rounded-lg border border-slate-200 px-2.5 py-2 text-sm text-slate-800 outline-none ring-cyan-200 transition focus:ring"
                  />
                </label>
                <button
                  type="button"
                  class="self-end rounded-lg border border-rose-200 px-2.5 py-2 text-[11px] font-bold uppercase tracking-wider text-rose-700 disabled:cursor-not-allowed disabled:opacity-40"
                  :disabled="signUpForm.accounts.length === 1"
                  @click="removeAccount(account.id)"
                >
                  Remove
                </button>
              </div>

              <div class="mt-3 grid grid-cols-[1fr_auto] items-end gap-2">
                <label class="block text-xs font-semibold text-slate-600">
                  Last 4 digits
                  <input
                    v-model="account.last4"
                    type="text"
                    inputmode="numeric"
                    maxlength="4"
                    required
                    placeholder="1234"
                    class="mt-1 w-full rounded-lg border border-slate-200 px-2.5 py-2 text-sm tracking-[0.2em] text-slate-800 outline-none ring-cyan-200 transition focus:ring"
                    @input="sanitizeLast4Input(account)"
                  />
                </label>

                <label class="mb-1 inline-flex items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-2 text-xs font-semibold text-slate-600">
                  <input
                    :id="`primary-${account.id}`"
                    :checked="account.isPrimary"
                    name="primary-account"
                    type="radio"
                    class="h-4 w-4 accent-cyan-600"
                    @change="setPrimary(account.id)"
                  />
                  Primary
                </label>
              </div>

              <p class="mt-2 text-[11px] font-medium text-slate-400">Account {{ index + 1 }}</p>
            </article>
          </div>
        </section>

        <button
          type="submit"
          :disabled="formBusy"
          class="w-full rounded-xl bg-cyan-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {{ formBusy ? 'Creating account...' : 'Create account' }}
        </button>
      </form>

      <form v-else class="space-y-4" @submit.prevent="submitSignIn">
        <label class="block text-xs font-semibold text-slate-600">
          Email
          <input
            v-model="signInForm.email"
            type="email"
            required
            autocomplete="email"
            class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none ring-cyan-200 transition focus:ring"
          />
        </label>

        <label class="block text-xs font-semibold text-slate-600">
          Password
          <input
            v-model="signInForm.password"
            type="password"
            required
            autocomplete="current-password"
            class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none ring-cyan-200 transition focus:ring"
          />
        </label>

        <button
          type="submit"
          :disabled="formBusy"
          class="w-full rounded-xl bg-cyan-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {{ formBusy ? 'Signing in...' : 'Sign in' }}
        </button>
      </form>

      <p v-if="formError" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
        {{ formError }}
      </p>
    </div>
  </main>
</template>
