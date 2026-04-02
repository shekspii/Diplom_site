const rawBase = import.meta.env.VITE_API_URL
const API_BASE = rawBase && rawBase.length > 0 ? rawBase : 'http://127.0.0.1:5000'

export function getAccessToken() {
  return localStorage.getItem('access_token')
}

export function clearAccessToken() {
  localStorage.removeItem('access_token')
}

export async function apiRequest(path, options = {}) {
  const token = options.auth ? getAccessToken() : null
  let response

  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {})
      },
      ...options
    })
  } catch {
    throw new Error('Не удалось соединиться с сервером.')
  }

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')
  const data = isJson ? await response.json().catch(() => ({})) : {}
  const fallbackText = !isJson ? await response.text().catch(() => '') : ''

  if (!response.ok) {
    const message =
      data?.error ||
      data?.msg ||
      data?.message ||
      fallbackText ||
      `Ошибка запроса (${response.status})`
    throw new Error(message)
  }

  return data
}
