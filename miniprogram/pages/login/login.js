// pages/login/login.js - 登录页
const api = require('../../utils/api.js')

Page({
  data: {
    username: '',
    password: '',
    loading: false
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  async handleLogin() {
    const { username, password } = this.data
    if (!username || !password) {
      wx.showToast({ title: '请输入用户名和密码', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    try {
      const res = await api.login(username, password)
      // 保存 token 和用户名
      wx.setStorageSync('token', res.access_token)
      wx.setStorageSync('username', res.username)
      // 跳转到首页（tabBar 页面用 switchTab）
      wx.switchTab({ url: '/pages/index/index' })
    } catch (err) {
      // 错误提示已在 api.js 中处理
    } finally {
      this.setData({ loading: false })
    }
  }
})
