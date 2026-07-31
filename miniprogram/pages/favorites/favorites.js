// pages/favorites/favorites.js - 收藏页
const api = require('../../utils/api.js')

Page({
  data: {
    favorites: [],
    loading: true
  },

  onShow() {
    this.loadFavorites()
  },

  onPullDownRefresh() {
    this.loadFavorites().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadFavorites() {
    this.setData({ loading: true })
    try {
      const res = await api.getFavorites()
      this.setData({ favorites: res || [] })
    } catch (err) {
      console.error('加载收藏失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  onTapArticle(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/detail/detail?id=${id}`
    })
  }
})
