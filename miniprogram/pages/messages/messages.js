// pages/messages/messages.js - 留言板：公开发布 + 定向发布
const api = require('../../utils/api.js')

Page({
  data: {
    messages: [],
    inputContent: '',
    loading: false,
    sending: false,
    page: 1,
    hasMore: true,
    total: 0,
    // 定向发布
    visibility: 'public',  // public | targeted
    visibleTo: '',         // 定向发布的用户名（逗号分隔）
    showTargetInput: false  // 是否显示用户名输入框
  },

  onLoad() {
    this.loadMessages(true)
  },

  onShow() {
    // 每次显示时刷新第一页
    this.loadMessages(true)
    // 更新已读时间
    const now = new Date()
    const pad = (n) => n.toString().padStart(2, '0')
    const timeStr = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes())
    wx.setStorageSync('lastReadMessageTime', timeStr)
  },

  // 加载留言
  async loadMessages(reset = false) {
    if (this.data.loading) return
    const page = reset ? 1 : this.data.page
    this.setData({ loading: true })

    try {
      console.log('[Messages] 加载留言, page=', page)
      const res = await api.getMessages(page)
      console.log('[Messages] 加载结果:', res)
      const newMessages = res.items || []
      const messages = reset ? newMessages : [...this.data.messages, ...newMessages]

      this.setData({
        messages,
        page: page + 1,
        hasMore: messages.length < res.total,
        total: res.total
      })
    } catch (err) {
      console.error('[Messages] 加载留言失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 上拉加载更多
  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadMessages(false)
    }
  },

  // 输入留言
  onInput(e) {
    this.setData({ inputContent: e.detail.value })
  },

  // 输入定向用户名
  onVisibleToInput(e) {
    this.setData({ visibleTo: e.detail.value })
  },

  // 切换公开/定向
  onToggleVisibility(e) {
    const vis = e.currentTarget.dataset.vis
    this.setData({
      visibility: vis,
      showTargetInput: vis === 'targeted'
    })
  },

  // 发送留言
  async onSend() {
    const content = this.data.inputContent.trim()
    if (!content) {
      wx.showToast({ title: '请输入留言内容', icon: 'none' })
      return
    }
    if (this.data.sending) return

    // 定向发布校验
    if (this.data.visibility === 'targeted') {
      const targets = this.data.visibleTo.trim()
      if (!targets) {
        wx.showToast({ title: '请输入至少一个用户名', icon: 'none' })
        return
      }
    }

    this.setData({ sending: true })

    try {
      console.log('[Messages] 发送留言:', content, this.data.visibility, this.data.visibleTo)
      await api.sendMessage(content, this.data.visibility, this.data.visibleTo)
      this.setData({ inputContent: '', visibleTo: '' })
      wx.showToast({ title: '留言成功', icon: 'success' })
      // 重置为公开发布
      this.setData({ visibility: 'public', showTargetInput: false })
      // 刷新留言列表
      this.loadMessages(true)
    } catch (err) {
      console.error('[Messages] 发送留言失败:', err)
      // api.js 已弹出错误提示，这里不再重复弹窗
    } finally {
      this.setData({ sending: false })
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadMessages(true).then(() => {
      wx.stopPullDownRefresh()
    })
  }
})
