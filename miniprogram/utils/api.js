// utils/api.js - API 请求封装
// 统一处理：callContainer 内网调用、token 注入、错误提示
// 优先使用 wx.cloud.callContainer 走内网，失败时降级到 wx.request 公网调用

// 公网降级 URL（callContainer 不可用时使用）
const FALLBACK_BASE_URL = 'https://senbai-289444-10-1460976929.sh.run.tcloudbase.com'

// 注意：不能在模块加载时调用 getApp()，因为此时 App() 可能尚未注册
// 延迟到每次请求时获取，确保 app 已就绪

/**
 * 发起请求（通过云托管内网 callContainer）
 * @param {string} url - 接口路径，如 /api/articles
 * @param {string} method - GET / POST
 * @param {object} data - 请求参数
 * @returns {Promise} - resolve(响应数据), reject(错误)
 */
function request(url, method = 'GET', data = {}) {
  const token = wx.getStorageSync('token')
  const app = getApp()
  const cloudEnv = (app && app.globalData) ? app.globalData.cloudEnv : 'prod-d8g8lkp1f325162b9'
  const serviceName = (app && app.globalData) ? app.globalData.serviceName : 'senbai'
  console.log('[API Request]', { url, method, data, hasToken: !!token, cloudEnv, serviceName })
  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: { env: cloudEnv },
      path: url,
      method: method,
      data: data,
      header: {
        'Content-Type': 'application/json',
        'X-WX-SERVICE': serviceName,
        'Authorization': token ? 'Bearer ' + token : ''
      },
      success(res) {
        console.log('[API Response]', { url, statusCode: res.statusCode, data: res.data })
        if (res.statusCode === 200) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // token 过期，跳转登录
          wx.removeStorageSync('token')
          wx.redirectTo({ url: '/pages/login/login' })
          reject(new Error('登录已过期'))
        } else {
          // 安全提取错误信息（res.data 可能是字符串、null 或非标准格式）
          let errMsg = '请求失败'
          if (res.data) {
            if (typeof res.data === 'string') {
              errMsg = res.data
            } else if (res.data.detail) {
              errMsg = typeof res.data.detail === 'string' ? res.data.detail : JSON.stringify(res.data.detail)
            } else {
              errMsg = JSON.stringify(res.data)
            }
          }
          console.error('[API Error]', { url, statusCode: res.statusCode, errMsg, rawData: res.data })
          wx.showToast({ title: errMsg, icon: 'none', duration: 3000 })
          reject(new Error(errMsg))
        }
      },
      fail(err) {
        console.error('[API callContainer Fail]', { url, method, err })
        // callContainer 失败，降级到公网 wx.request
        console.log('[API] 降级到公网请求:', FALLBACK_BASE_URL + url)
        _requestFallback(url, method, data, token, resolve, reject)
      }
    })
  })
}

/**
 * 公网降级请求（callContainer 不可用时使用）
 */
function _requestFallback(url, method, data, token, resolve, reject) {
  wx.request({
    url: FALLBACK_BASE_URL + url,
    method: method,
    data: data,
    header: {
      'Content-Type': 'application/json',
      'Authorization': token ? 'Bearer ' + token : ''
    },
    success(res) {
      console.log('[API Fallback Response]', { url, statusCode: res.statusCode, data: res.data })
      if (res.statusCode === 200) {
        resolve(res.data)
      } else if (res.statusCode === 401) {
        wx.removeStorageSync('token')
        wx.redirectTo({ url: '/pages/login/login' })
        reject(new Error('登录已过期'))
      } else {
        let errMsg = '请求失败'
        if (res.data) {
          if (typeof res.data === 'string') {
            errMsg = res.data
          } else if (res.data.detail) {
            errMsg = typeof res.data.detail === 'string' ? res.data.detail : JSON.stringify(res.data.detail)
          } else {
            errMsg = JSON.stringify(res.data)
          }
        }
        console.error('[API Fallback Error]', { url, statusCode: res.statusCode, errMsg, rawData: res.data })
        wx.showToast({ title: errMsg, icon: 'none', duration: 3000 })
        reject(new Error(errMsg))
      }
    },
    fail(err) {
      console.error('[API Fallback Fail]', { url, method, err })
      wx.showToast({ title: '网络异常: ' + (err.errMsg || ''), icon: 'none', duration: 3000 })
      reject(err)
    }
  })
}

// ========== 具体接口 ==========

// 登录
function login(username, password) {
  return request('/api/auth/login', 'POST', { username, password })
}

// 注册
function register(username, password) {
  return request('/api/auth/register', 'POST', { username, password })
}

// 获取资讯流
function getArticles(page = 1, pageSize = 20) {
  return request(`/api/articles?page=${page}&page_size=${pageSize}`)
}

// 获取资讯详情
function getArticleDetail(id) {
  return request(`/api/articles/${id}`)
}

// 喜欢/不喜欢反馈
function feedback(articleId, feedback) {
  return request(`/api/articles/${articleId}/feedback`, 'POST', { feedback })
}

// 收藏/取消收藏
function toggleFavorite(articleId) {
  return request(`/api/articles/${articleId}/favorite`, 'POST')
}

// 获取所有行业
function getIndustries() {
  return request('/api/industries')
}

// 获取我关注的行业
function getMyIndustries() {
  return request('/api/users/me/industries')
}

// 设置我关注的行业
function setMyIndustries(industryIds) {
  return request('/api/users/me/industries', 'POST', { industry_ids: industryIds })
}

// 获取收藏列表
function getFavorites() {
  return request('/api/users/me/favorites')
}

// 手动获取最新资讯 + AI总结（异步触发，消耗Token，用户主动点击触发）
function refreshArticles() {
  return request('/api/articles/refresh', 'POST')
}

// 查询刷新进度
function getRefreshStatus() {
  return request('/api/articles/refresh/status')
}

// 获取每日精选大事（按行业分组，默认最近5天）
function getDigest(targetDate, days) {
  let params = []
  if (targetDate) params.push('target_date=' + targetDate)
  if (days) params.push('days=' + days)
  const query = params.length > 0 ? '?' + params.join('&') : ''
  return request(`/api/articles/digest${query}`)
}

// 获取留言列表
function getMessages(page = 1) {
  return request(`/api/messages?page=${page}`)
}

// 发送留言（支持定向发布）
function sendMessage(content, visibility, visibleTo) {
  return request('/api/messages', 'POST', {
    content,
    visibility: visibility || 'public',
    visible_to: visibleTo || ''
  })
}

// 获取未读留言数
function getUnreadCount(since) {
  const param = since ? '?since=' + encodeURIComponent(since) : ''
  return request('/api/messages/unread-count' + param)
}

module.exports = {
  request,
  login,
  register,
  getArticles,
  getArticleDetail,
  feedback,
  toggleFavorite,
  getIndustries,
  getMyIndustries,
  setMyIndustries,
  getFavorites,
  refreshArticles,
  getRefreshStatus,
  getDigest,
  getMessages,
  sendMessage,
  getUnreadCount
}
