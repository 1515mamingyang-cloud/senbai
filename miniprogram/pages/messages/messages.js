// pages/messages/messages.js - 留言板：公共留言，所有用户互通
const api = require('../../utils/api.js')

Page({
  data: {
    messages: [],
    inputContent: '',
    loading: false,
    sending: false,
    page: 1,
    hasMore: true,
    total: 0
  },

  onLoad() {
    this.loadMessages(true)
  },

  onShow() {
    // 每次显示时刷新第一页
    this.loadMessages(true)
  },

  // 加载留言
  async loadMessages(reset = false) {
    if (this.data.loading) return
    const page = reset ? 1 : this.data.page
    this.setData({ loading: true })

    try {
      const res = await api.getMessages(page)
      const newMessages = res.items || []
      const messages = reset ? newMessages : [...this.data.messages, ...newMessages]

      this.setData({
        messages,
        page: page + 1,
        hasMore: messages.length < res.total,
        total: res.total
      })
    } catch (err) {
      console.error('加载留言失败:', err)
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

  // 发送留言
  async onSend() {
    const content = this.data.inputContent.trim()
    if (!content) {
      wx.showToast({ title: '请输入留言内容', icon: 'none' })
      return
    }
    if (this.data.sending) return
    this.setData({ sending: true })

    try {
      await api.sendMessage(content)
      this.setData({ inputContent: '' })
      wx.showToast({ title: '留言成功', icon: 'success' })
      // 刷新留言列表
      this.loadMessages(true)
    } catch (err) {
      console.error('发送留言失败:', err)
      wx.showToast({ title: '发送失败', icon: 'none' })
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
