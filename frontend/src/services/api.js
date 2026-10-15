const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, options)
  } catch {
    throw new Error(`Cannot reach the backend at ${BASE_URL}. Start the FastAPI server and check VITE_API_BASE_URL.`)
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || data.message || `Request failed (${response.status})`)
  }
  return data
}

export const api = {
  health: () => request('/api/health'),
  contractInfo: () => request('/api/contract-info'),
  history: () => request('/api/history'),
  verify: (file, certificateId) => {
    const form = new FormData()
    form.append('file', file)
    if (certificateId.trim()) form.append('certificate_id', certificateId.trim())
    return request('/api/verify', { method: 'POST', body: form })
  }
}

export { BASE_URL }
