import axios from 'axios'
import { showToast } from 'vant'

/** axios 实例：请求自动携带 JWT，错误统一 Toast 提示 */
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 10000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  (res) => res,
  (err) => {
    const response = err.response
    let message = '网络异常，请稍后重试'

    if (!response) {
      // 无 response：真正的网络层失败（断网 / 超时 / 跨域）
      message = err?.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '网络异常，请检查网络或后端服务'
    } else {
      const detail: unknown = response.data?.detail
      if (typeof detail === 'string') {
        message = detail
      } else if (Array.isArray(detail) && detail.length > 0) {
        // FastAPI 422 参数校验：detail 是数组
        const first = detail[0] as { msg?: string; loc?: unknown[] }
        message = first?.msg ? `参数错误：${first.msg}` : '请求参数有误'
      } else if (typeof response.data === 'string' && response.data.trim()) {
        // 500 等以纯文本返回的错误体
        message = `服务错误(${response.status})`
      } else {
        message = `请求失败(${response.status})`
      }
    }

    showToast({ message, type: 'fail' })
    return Promise.reject(err)
  },
)

export default request
