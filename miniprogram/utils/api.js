// utils/api.js - API 请求封装
// 统一处理：callContainer 内网调用、token 注入、错误提示
// 使用 wx.cloud.callContainer 走内网，无需配置服务器域名

const app = getApp()

/**
 * 发起请求（通过云托管内网 callContainer）
 * @param {string} url - 接口路径，如 /api/articles
 * @param {string} method - GET / POST
 * @param {object} data - 请求参数
 * @returns {Promise} - resolve(响应数据), reject(错误)
 */
function request(url, method = 'GET', data = {}) {
  const token = wx.getStorageSync('token')
  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: { env: app.globalData.cloudEnv },
      path: url,
      method: method,
      data: data,
      header: {
        'Content-Type': 'application/json',
        'X-WX-SERVICE': app.globalData.serviceName,
        'Authorization': token ? 'Bearer ' + token : ''
      },
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // token 过期，跳转登录
          wx.removeStorageSync('token')
          wx.redirectTo({ url: '/pages/login/login' })
          reject(new Error('登录已过期'))
        } else {
          wx.showToast({ title: res.data.detail || '请求失败', icon: 'none' })
          reject(new Error(res.data.detail || '请求失败'))
        }
      },
      fail(err) {
        wx.showToast({ title: '网络异常', icon: 'none' })
        reject(err)
      }
    })
  })
}

// ========== 具体接口 ==========

// 登录
function login(username, password) {
  return request('/api/auth/login', 'POST', { username, password })
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

// 获取每日精选大事（按行业分组）
function getDigest(targetDate) {
  const param = targetDate ? `?target_date=${targetDate}` : ''
  return request(`/api/articles/digest${param}`)
}

// 获取留言列表
function getMessages(page = 1) {
  return request(`/api/messages?page=${page}`)
}

// 发送留言
function sendMessage(content) {
  return request('/api/messages', 'POST', { content })
}

module.exports = {
  request,
  login,
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
  sendMessage
}
