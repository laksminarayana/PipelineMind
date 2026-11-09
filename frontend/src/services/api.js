const API_BASE = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })
  const text = await response.text()
  let result
  try { result = text ? JSON.parse(text) : null } catch { result = text }
  if (!response.ok) {
    const message = typeof result === 'object' && result?.detail ? result.detail : `Request failed (${response.status})`
    throw new Error(message)
  }
  return result
}

export const api = {
  get: (path) => request(path),
  post: (path, data) => request(path, { method: 'POST', body: JSON.stringify(data) }),
}
