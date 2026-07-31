// pages/profile/profile.js - 我的：行业选择、设置
const api = require('../../utils/api.js')

Page({
  data: {
    username: '',
    industries: [],        // 所有行业
    selectedIds: [],       // 已选中的行业 ID
    loading: true,
    saving: false
  },

  onShow() {
    const username = wx.getStorageSync('username') || '用户'
    this.setData({ username })
    this.loadData()
  },

  async loadData() {
    this.setData({ loading: true })
    try {
      // 并行加载：所有行业 + 我已关注的行业
      const [allIndustries, myIndustries] = await Promise.all([
        api.getIndustries(),
        api.getMyIndustries()
      ])

      // 标记已选中的行业
      const selectedIds = (myIndustries || []).map(i => i.id)
      const industries = (allIndustries || []).map(i => ({
        ...i,
        checked: selectedIds.includes(i.id)
      }))

      this.setData({ industries, selectedIds })
    } catch (err) {
      console.error('加载数据失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 切换行业选中状态
  onToggleIndustry(e) {
    const id = e.currentTarget.dataset.id
    const industries = this.data.industries.map(i => {
      if (i.id === id) {
        return { ...i, checked: !i.checked }
      }
      return i
    })
    const selectedIds = industries.filter(i => i.checked).map(i => i.id)
    this.setData({ industries, selectedIds })
  },

  // 保存关注行业
  async onSave() {
    if (this.data.selectedIds.length === 0) {
      wx.showToast({ title: '请至少选择一个行业', icon: 'none' })
      return
    }

    this.setData({ saving: true })
    try {
      await api.setMyIndustries(this.data.selectedIds)
      wx.showToast({ title: '保存成功', icon: 'success' })
    } catch (err) {
      // 错误提示已在 api.js 中处理
    } finally {
      this.setData({ saving: false })
    }
  },

  // 退出登录
  onLogout() {
    wx.showModal({
      title: '确认退出',
      content: '退出后需要重新登录',
      success(res) {
        if (res.confirm) {
          wx.removeStorageSync('token')
          wx.removeStorageSync('username')
          wx.redirectTo({ url: '/pages/login/login' })
        }
      }
    })
  }
})
