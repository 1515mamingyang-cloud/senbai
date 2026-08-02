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

// 没鱼时的提示
const NO_FISH_RESPONSES = [
  '喵...鱼库空了，去钓鱼吧！',
  '喵呜~森柏好饿，去路亚粮仓钓几条嘛~',
  '蹭蹭~没有鱼了，主人去钓鱼好不好？'
]

Page({
  data: {
    digestDate: '',
    industries: [],
    loading: false,
    username: '',
    // 小猫互动
    catAnimating: false,
    catBubbleText: '',
    catBubbleShow: false,
    // 鱼库存
    fishStock: 10,
    // 用户已选行业
    selectedIndustryIds: [],
    hasSelectedIndustries: false,
    // 留言未读
    unreadMessages: 0
  },

  onLoad() {
    const username = wx.getStorageSync('username') || '用户'
    this.setData({ username })
    this._loadFishStock()
  },

  onShow() {
    // 检查用户已选行业，再决定加载哪些内容
    this._checkIndustriesAndLoad()
    // 从路亚页面返回时刷新鱼库存
    this._loadFishStock()
    // 检查留言未读数
    this._checkUnreadMessages()
  },

  // 下拉刷新
  onPullDownRefresh() {
    this._checkIndustriesAndLoad().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  // 检查用户已选行业 → 决定加载
  async _checkIndustriesAndLoad() {
    try {
      const myIndustries = await api.getMyIndustries()
      const ids = (myIndustries || []).map(i => i.id)
      const hasSelected = ids.length > 0
      this.setData({
        selectedIndustryIds: ids,
        hasSelectedIndustries: hasSelected
      })
      if (hasSelected) {
        this.loadDigest()
      } else {
        // 没选行业，清空内容
        this.setData({ industries: [], digestDate: '' })
      }
    } catch (err) {
      console.error('检查行业失败:', err)
      // 可能未登录，不影响
    }
  },

  // 加载每日精选（只显示用户选了的行业，最近5天）
  async loadDigest() {
    if (this.data.loading) return
    this.setData({ loading: true })

    try {
      const res = await api.getDigest(null, 5)
      // 过滤：只显示用户选了的行业
      const selectedIds = this.data.selectedIndustryIds
      const filtered = (res.industries || []).filter(g =>
        selectedIds.includes(g.industry_id)
      )
      // 日期范围显示
      const dates = res.dates || []
      let dateText = ''
      if (dates.length > 0) {
        dateText = dates[0]
        if (dates.length > 1) {
          dateText += ' ~ ' + dates[dates.length - 1]
        }
      }
      this.setData({
        digestDate: dateText,
        industries: filtered
      })
    } catch (err) {
      console.error('加载精选失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 手动刷新（只从库读取，不触发爬取）
  onRefresh() {
    this.loadDigest()
  },

  // 检查留言未读数
  async _checkUnreadMessages() {
    try {
      const lastRead = wx.getStorageSync('lastReadMessageTime') || ''
      const res = await api.getUnreadCount(lastRead)
      this.setData({ unreadMessages: res.unread || 0 })
    } catch (err) {
      console.error('检查未读留言失败:', err)
    }
  },

  // 跳转到行业选择页（我的页面）
  goSelectIndustries() {
    wx.switchTab({ url: '/pages/profile/profile' })
  },

  // 点击精选卡片 → 跳转详情页
  onTapArticle(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/detail/detail?id=${id}`
    })
  },

  // 点击小猫 → 跳转留言板（清除未读标记）
  onTapCat() {
    // 记录当前时间为已读时间
    const now = new Date()
    const pad = (n) => n.toString().padStart(2, '0')
    const timeStr = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes())
    wx.setStorageSync('lastReadMessageTime', timeStr)
    this.setData({ unreadMessages: 0 })
    wx.navigateTo({
      url: '/pages/messages/messages'
    })
  },

  // 点击路亚粮仓 → 跳转路亚游戏
  onTapLure() {
    wx.navigateTo({
      url: '/pages/lure/lure'
    })
  },

  // 读取鱼库存
  _loadFishStock() {
    const stock = wx.getStorageSync('fishStock')
    this.setData({ fishStock: stock !== '' && stock !== undefined ? stock : 10 })
    if (stock === '' || stock === undefined) {
      wx.setStorageSync('fishStock', 10)
    }
  },

  // 投喂小猫
  onFeedCat() {
    // 检查鱼库存
    if (this.data.fishStock <= 0) {
      const text = NO_FISH_RESPONSES[Math.floor(Math.random() * NO_FISH_RESPONSES.length)]
      this.setData({
        catAnimating: true,
        catBubbleText: text,
        catBubbleShow: true
      })
      setTimeout(() => { this.setData({ catAnimating: false }) }, 600)
      setTimeout(() => { this.setData({ catBubbleShow: false }) }, 2800)
      return
    }
    // 消耗一条鱼
    const newStock = this.data.fishStock - 1
    wx.setStorageSync('fishStock', newStock)
    this.setData({ fishStock: newStock })
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
  }
})
