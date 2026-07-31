// pages/index/index.js - 首页：森柏助手 + 每日精选大事
const api = require('../../utils/api.js')

// 撒娇文字池
const FEED_RESPONSES = [
  '喵~谢谢小鱼干！',
  '嗷呜嗷呜~好好吃！',
  '森柏最喜欢吃鱼了~',
  '再来一条嘛~喵',
  '吧唧吧唧~真香！',
  '喵呜~吃饱饱了~'
]

const PET_RESPONSES = [
  '呼噜呼噜~好舒服',
  '喵呜~再摸摸我~',
  '蹭蹭你~好喜欢',
  '森柏被摸摸好开心~',
  '咕噜咕噜~不要停~',
  '喵~你的手好温暖~'
]

Page({
  data: {
    digestDate: '',
    industries: [],
    loading: false,
    refreshing: false,
    username: '',
    // 小猫互动
    catAnimating: false,
    catBubbleText: '',
    catBubbleShow: false
  },

  onLoad() {
    const username = wx.getStorageSync('username') || '用户'
    this.setData({ username })
  },

  onShow() {
    this.loadDigest()
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadDigest().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  // 加载每日精选
  async loadDigest() {
    if (this.data.loading) return
    this.setData({ loading: true })

    try {
      const res = await api.getDigest()
      this.setData({
        digestDate: res.date || '',
        industries: res.industries || []
      })
    } catch (err) {
      console.error('加载精选失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 点击精选卡片 → 跳转详情页
  onTapArticle(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/detail/detail?id=${id}`
    })
  },

  // 点击小猫 → 跳转留言板
  onTapCat() {
    wx.navigateTo({
      url: '/pages/messages/messages'
    })
  },

  // 投喂小猫
  onFeedCat() {
    this._interactWithCat(FEED_RESPONSES)
  },

  // 抚摸小猫
  onPetCat() {
    this._interactWithCat(PET_RESPONSES)
  },

  // 小猫互动核心逻辑
  _interactWithCat(responses) {
    // 如果正在动画中，不重复触发
    if (this.data.catAnimating) return

    // 随机选一句撒娇文字
    const text = responses[Math.floor(Math.random() * responses.length)]

    // 触发动画 + 显示气泡
    this.setData({
      catAnimating: true,
      catBubbleText: text,
      catBubbleShow: true
    })

    // 动画结束后取消动画class
    setTimeout(() => {
      this.setData({ catAnimating: false })
    }, 600)

    // 2.5秒后隐藏气泡
    setTimeout(() => {
      this.setData({ catBubbleShow: false })
    }, 2500)
  },

  // 手动刷新：爬取+AI总结（异步）
  async onTapRefresh() {
    if (this.data.refreshing) return
    this.setData({ refreshing: true })
    wx.showLoading({ title: '开始获取...', mask: true })

    try {
      await api.refreshArticles()

      // 轮询状态（每3秒查一次，最多120秒）
      const maxAttempts = 40
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise(resolve => setTimeout(resolve, 3000))
        const status = await api.getRefreshStatus()

        if (status.status === 'done') {
          wx.hideLoading()
          const msg = `新增${status.new_articles || 0}篇，生成${status.digest_count || 0}条精选`
          wx.showToast({ title: msg, icon: 'none', duration: 3000 })
          this.loadDigest()
          return
        } else if (status.status === 'error') {
          wx.hideLoading()
          wx.showToast({ title: '获取失败: ' + (status.error || ''), icon: 'none', duration: 3000 })
          return
        } else {
          wx.showLoading({ title: `获取中(${status.elapsed || 0}s)...`, mask: true })
        }
      }

      wx.hideLoading()
      wx.showToast({ title: '获取超时，请稍后查看', icon: 'none', duration: 3000 })
      this.loadDigest()
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '获取失败，请稍后重试', icon: 'none' })
      console.error('刷新失败:', err)
    } finally {
      this.setData({ refreshing: false })
    }
  }
})
