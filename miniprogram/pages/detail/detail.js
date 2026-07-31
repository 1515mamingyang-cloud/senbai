// pages/detail/detail.js - 资讯详情页
const api = require('../../utils/api.js')

Page({
  data: {
    article: null,    // 文章详情
    favorited: false, // 是否已收藏
    feedback: 0,      // 1=喜欢, -1=不喜欢, 0=未反馈
    loading: true
  },

  onLoad(options) {
    const id = options.id
    this.loadDetail(id)
  },

  async loadDetail(id) {
    try {
      const res = await api.getArticleDetail(id)
      this.setData({ article: res, loading: false })
    } catch (err) {
      this.setData({ loading: false })
    }
  },

  // 喜欢
  async onLike() {
    const id = this.data.article.id
    const newFeedback = this.data.feedback === 1 ? 0 : 1  // 再次点击取消
    try {
      await api.feedback(id, newFeedback)
      this.setData({ feedback: newFeedback })
      wx.showToast({
        title: newFeedback === 1 ? '已喜欢' : '已取消',
        icon: 'none'
      })
    } catch (err) {}
  },

  // 不喜欢
  async onDislike() {
    const id = this.data.article.id
    const newFeedback = this.data.feedback === -1 ? 0 : -1
    try {
      await api.feedback(id, newFeedback)
      this.setData({ feedback: newFeedback })
      wx.showToast({
        title: newFeedback === -1 ? '已不喜欢' : '已取消',
        icon: 'none'
      })
    } catch (err) {}
  },

  // 收藏/取消收藏
  async onFavorite() {
    const id = this.data.article.id
    try {
      const res = await api.toggleFavorite(id)
      this.setData({ favorited: res.favorited })
      wx.showToast({
        title: res.favorited ? '已收藏' : '已取消收藏',
        icon: 'none'
      })
    } catch (err) {}
  },

  // 打开原文链接（复制到剪贴板，小程序内不能直接打开外链）
  onCopyLink() {
    wx.setClipboardData({
      data: this.data.article.source_url,
      success() {
        wx.showToast({ title: '链接已复制', icon: 'success' })
      }
    })
  }
})
