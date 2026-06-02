const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '::1'])

const isLocalHost = (host) => LOCAL_HOSTS.has(String(host || '').toLowerCase())

const safeUrl = (value) => {
  try {
    return new URL(value)
  } catch {
    return null
  }
}

const resolveDefaultBackendBaseUrl = () => {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8010'
  }

  const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
  const hostname = window.location.hostname || '127.0.0.1'
  return `${protocol}//${hostname}:8010`
}

const normalizeConfiguredBackendUrl = (configuredValue) => {
  const configured = String(configuredValue ?? '').trim()
  if (!configured) {
    return ''
  }

  if (typeof window === 'undefined') {
    return configured
  }

  const parsed = safeUrl(configured)
  const pageHost = window.location.hostname || ''

  if (!parsed || !pageHost || isLocalHost(pageHost)) {
    return configured
  }

  if (!isLocalHost(parsed.hostname)) {
    return configured
  }

  parsed.hostname = pageHost
  if (!parsed.port) {
    parsed.port = '8010'
  }
  return parsed.toString()
}

export const resolveBackendBaseUrl = (configuredValue) => {
  const normalizedConfigured = normalizeConfiguredBackendUrl(configuredValue)
  const selected = normalizedConfigured || resolveDefaultBackendBaseUrl()
  return String(selected).replace(/\/$/, '')
}

export default resolveBackendBaseUrl