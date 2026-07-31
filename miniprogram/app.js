// app.js - 森柏小程序入口
App({
  onLaunch() {
    // 初始化微信云托管环境（用于 callContainer 内网调用，无需配置服务器域名）
    wx.cloud.init({
      env: 'prod-d8g8lkp1f325162b9'
    })

    // 检查登录状态
    const token = wx.getStorageSync('token')
    if (!token) {
      // 未登录，跳转登录页
      wx.redirectTo({ url: '/pages/login/login' })
    }
  },

  globalData: {
    // 云托管环境ID和服务名（用于 callContainer 内网调用）
    cloudEnv: 'prod-d8g8lkp1f325162b9',
    serviceName: 'senbai',
    userInfo: null
  }
})
