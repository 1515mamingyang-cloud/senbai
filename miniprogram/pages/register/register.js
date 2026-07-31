// pages/register/register.js - 用户注册
const api = require('../../utils/api.js')

Page({
  data: {
    username: '',
    password: '',
    confirmPassword: '',
    loading: false
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  onConfirmPasswordInput(e) {
    this.setData({ confirmPassword: e.detail.value })
  },

  async handleRegister() {
    const { username, password, confirmPassword } = this.data

    if (!username || !password) {
      wx.showToast({ title: '请输入用户名和密码', icon: 'none' })
      return
    }
    if (username.trim().length < 2) {
      wx.showToast({ title: '用户名至少2个字符', icon: 'none' })
      return
    }
    if (password.trim().length < 4) {
      wx.showToast({ title: '密码至少4个字符', icon: 'none' })
      return
    }
    if (password !== confirmPassword) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    try {
      const res = await api.register(username.trim(), password.trim())
      // 注册成功，自动登录
      wx.setStorageSync('token', res.access_token)
      wx.setStorageSync('username', res.username)
      wx.showToast({ title: '注册成功', icon: 'success' })
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' })
      }, 1000)
    } catch (err) {
      // 错误提示已在 api.js 中处理
    } finally {
      this.setData({ loading: false })
    }
  },

  // 返回登录页
  goBack() {
    wx.navigateBack()
  }
})
