// pages/lure/lure.js - 喵的路亚粮仓：路亚钓鱼模拟游戏 V2

// ===== 鱼饵配置（每种对应不同鱼种，带可爱图片） =====
const BAITS = [
  { id: 'ttail',   name: 'T尾',       img: '/images/baits/bait_ttail.png',   fish: '鲈鱼',   fishIcon: '🐟', rarity: 'common',   desc: '底层慢搜，专攻鲈鱼' },
  { id: 'minnow',  name: '米诺',       img: '/images/baits/bait_minnow.png',  fish: '翘嘴',   fishIcon: '🐟', rarity: 'common',   desc: '中层泳姿，诱钓翘嘴' },
  { id: 'popper',  name: '波趴',       img: '/images/baits/bait_popper.png',  fish: '黑鱼',   fishIcon: '🐠', rarity: 'uncommon', desc: '水面炸水，专钓黑鱼' },
  { id: 'vib',     name: 'VIB振动饵',  img: '/images/baits/bait_vib.png',     fish: '鳜鱼',   fishIcon: '🐡', rarity: 'rare',     desc: '全层搜索，鳜鱼克星' },
  { id: 'jig',     name: '铁板',       img: '/images/baits/bait_jig.png',     fish: '海鲈鱼', fishIcon: '🐠', rarity: 'uncommon', desc: '远投深水，海鲈专攻' },
]

// ===== 加速度阈值（g，总幅度含重力，静止约1g） =====
const ACC = {
  CAST_MIN:   2.0,  // 最小有效甩动力度
  CAST_MAX:   4.0,  // 超过此值炸线
  HOOK_MIN:   2.5,  // 刺鱼最小有效力度
}

// ===== 撒娇文字 =====
const CAT_FEED_LINES = [
  '喵呜~森柏好开心！',
  '嗷呜嗷呜~好多鱼！',
  '喵~森柏吃饱饱了~',
  '吧唧吧唧~谢谢主人！',
  '蹭蹭你~森柏最爱你了~',
]

// ===== 震动工具函数（带fallback和日志） =====
function vibrate(type) {
  if (type === 'long') {
    wx.vibrateLong({
      success: function() { console.log('[Vibrate] Long OK') },
      fail: function(err) {
        console.error('[Vibrate] Long failed:', err)
        // 降级用短震动
        wx.vibrateShort({
          type: 'heavy',
          success: function() { console.log('[Vibrate] Short fallback OK') },
          fail: function(e) { console.error('[Vibrate] Short fallback failed:', e) }
        })
      }
    })
  } else {
    wx.vibrateShort({
      type: type || 'heavy',
      success: function() { console.log('[Vibrate] Short OK:', type) },
      fail: function(err) {
        console.error('[Vibrate] Short failed:', err)
        // 再试一次不带type参数（兼容旧版基础库）
        wx.vibrateShort({
          success: function() { console.log('[Vibrate] Short (no type) OK') },
          fail: function(e) { console.error('[Vibrate] All vibration failed:', e) }
        })
      }
    })
  }
}

Page({
  data: {
    // 游戏状态: idle -> ready -> flying -> reeling -> bite -> catch/escape/fail -> idle
    state: 'idle',
    selectedBait: null,
    selectedBaitId: '',
    castDistance: 0,
    statusText: '选择一种鱼饵开始作钓',
    // 鱼饵列表
    baits: BAITS,
    // 鱼获
    caughtFish: [],
    fishStock: 10,
    // UI弹窗
    showFishBox: false,
    showFeedModal: false,
    feedResult: '',
    // 收线
    reelProgress: 0,
    reelAngle: 0,
    reelSpinning: false, // 纺车轮是否在转
    // 钓到的鱼（展示用）
    lastCatch: null,
    showCatchAnim: false,
  },

  // ===== 非data实例变量 =====
  _accCallback: null,
  _reelCenter: null,
  _lastAngle: null,
  _angleAccum: 0,
  _hookTimeout: null,
  _resetTimer: null,
  _landTimer: null,     // 自动落水定时器
  _reelStopTimer: null, // 纺车轮停止定时器
  // 中鱼判定（V4：按收线进度+距离+速度）
  _biteChance: 0,       // 基础中鱼概率（距离决定 0.6~0.8）
  _biteThreshold: 0,    // 中鱼判定进度点（25%~75%）
  _biteChecked: false,  // 是否已做过中鱼判定
  _reelSpeeds: [],      // 收线速度采样（ms per 1% progress）
  _lastProgressTime: null,

  onLoad() {
    this._loadStorage()
  },

  onShow() {
    this._loadStorage()
  },

  onUnload() {
    this._cleanup()
  },

  onHide() {
    this._cleanup()
  },

  // 清理所有监听器和定时器
  _cleanup() {
    try { wx.stopAccelerometer() } catch(e) {}
    try { wx.offAccelerometerChange() } catch(e) {}
    if (this._hookTimeout) { clearTimeout(this._hookTimeout); this._hookTimeout = null }
    if (this._resetTimer) { clearTimeout(this._resetTimer); this._resetTimer = null }
    if (this._landTimer) { clearTimeout(this._landTimer); this._landTimer = null }
    if (this._reelStopTimer) { clearTimeout(this._reelStopTimer); this._reelStopTimer = null }
  },

  // 读取本地存储
  _loadStorage() {
    const stock = wx.getStorageSync('fishStock')
    const caught = wx.getStorageSync('fishCaught')
    this.setData({
      fishStock: stock !== '' && stock !== undefined ? stock : 10,
      caughtFish: caught || []
    })
    if (stock === '' || stock === undefined) {
      wx.setStorageSync('fishStock', 10)
    }
  },

  // ===== 选择鱼饵 =====
  selectBait(e) {
    if (this.data.state !== 'idle') return
    const id = e.currentTarget.dataset.id
    const bait = BAITS.find(function(b) { return b.id === id })
    this.setData({
      selectedBait: bait,
      selectedBaitId: id,
      statusText: '已选「' + bait.name + '」\n按住"准备"按钮，甩手机抛饵'
    })
  },

  // ===== 抛投阶段 =====
  onReadyStart() {
    if (this.data.state !== 'idle' || !this.data.selectedBait) return

    this.setData({
      state: 'ready',
      statusText: '保持按住！甩手机抛饵！'
    })

    wx.startAccelerometer({ interval: 'game' })
    var self = this
    this._accCallback = function(res) {
      if (self.data.state !== 'ready') return
      var acc = Math.sqrt(res.x * res.x + res.y * res.y + res.z * res.z)
      if (acc > ACC.CAST_MIN) {
        self._handleCast(acc)
      }
    }
    wx.onAccelerometerChange(this._accCallback)
  },

  onReadyEnd() {
    if (this.data.state !== 'ready') return
    wx.stopAccelerometer()
    wx.offAccelerometerChange()
    this._accCallback = null
    this.setData({
      state: 'idle',
      statusText: '需要甩手机才能抛出鱼饵\n按住"准备"同时甩手机'
    })
  },

  // 处理抛投结果
  _handleCast(acc) {
    wx.stopAccelerometer()
    wx.offAccelerometerChange()
    this._accCallback = null

    if (acc > ACC.CAST_MAX) {
      this.setData({
        state: 'fail',
        statusText: '💥 炸线了！力度太大了',
      })
      var self = this
      this._resetTimer = setTimeout(function() {
        self._resetToIdle('调整力度，再来一次')
      }, 2200)
      return
    }

    // 计算抛投距离（15~80米）
    var distance = Math.round(Math.min(80, Math.max(15, (acc - 1.0) * 22)))

    this.setData({
      state: 'flying',
      castDistance: distance,
      statusText: '抛出 ' + distance + ' 米！\n饵正在飞行...'
    })

    // 2秒后自动落水（飞行动画时长）
    var self = this
    this._landTimer = setTimeout(function() {
      if (self.data.state === 'flying') {
        self._startReeling()
      }
    }, 2000)
  },

  // ===== 自动落水 -> 收线 =====
  _startReeling() {
    // V4: 中鱼概率由抛投距离决定（15m=60%, 80m=80%）
    var dist = this.data.castDistance
    var baseChance = 0.6 + (dist - 15) / 65 * 0.2  // 0.6 ~ 0.8

    // 随机选择中鱼判定进度点（25%~75%之间）
    var biteThreshold = 25 + Math.floor(Math.random() * 51)

    this._biteChance = baseChance
    this._biteThreshold = biteThreshold
    this._biteChecked = false
    this._reelSpeeds = []
    this._lastProgressTime = null

    this.setData({
      state: 'reeling',
      statusText: '手指在圆环上画圈收线\n耐心等待鱼咬钩...',
      reelProgress: 0,
      reelAngle: 0,
      reelSpinning: false
    })

    this._angleAccum = 0
    this._lastAngle = null
    // 不再设置定时器，中鱼判定在收线进度达到阈值时触发
  },

  // 收线触摸：开始
  onReelStart(e) {
    if (this.data.state !== 'reeling') return
    var self = this
    var query = wx.createSelectorQuery()
    query.select('.reel-ring').boundingClientRect(function(rect) {
      if (rect) {
        self._reelCenter = {
          x: rect.left + rect.width / 2,
          y: rect.top + rect.height / 2
        }
      }
    }).exec()
  },

  // 收线触摸：移动（画圈）
  onReelMove(e) {
    if (this.data.state !== 'reeling') return
    if (!this._reelCenter || !e.touches[0]) return

    var touch = e.touches[0]
    var dx = touch.clientX - this._reelCenter.x
    var dy = touch.clientY - this._reelCenter.y
    // V3: 不再限制最小距离，整个圆内任意位置画圈都算
    var angle = Math.atan2(dy, dx)

    if (this._lastAngle !== null) {
      var delta = angle - this._lastAngle
      if (delta > Math.PI) delta -= 2 * Math.PI
      if (delta < -Math.PI) delta += 2 * Math.PI
      this._angleAccum += Math.abs(delta)

      // 每圈（2π）增加8%进度（之前是15%，现在更慢）
      var progress = Math.min(100, Math.floor((this._angleAccum / (2 * Math.PI)) * 8))
      var reelAngle = Math.round((this._angleAccum * 180 / Math.PI) % 360)

      if (progress !== this.data.reelProgress) {
        // 记录收线速度（每次进度变化的时间间隔）
        var now = Date.now()
        if (this._lastProgressTime) {
          var dt = now - this._lastProgressTime
          this._reelSpeeds.push(dt)
          if (this._reelSpeeds.length > 10) this._reelSpeeds.shift()
        }
        this._lastProgressTime = now

        // 启动纺车轮旋转
        if (this._reelStopTimer) { clearTimeout(this._reelStopTimer); this._reelStopTimer = null }
        this.setData({
          reelProgress: progress,
          reelAngle: reelAngle,
          reelSpinning: true
        })
        // 0.5秒不动画就停转
        var self = this
        this._reelStopTimer = setTimeout(function() {
          self.setData({ reelSpinning: false })
        }, 500)

        // V4: 中鱼判定 —— 达到阈值进度时触发
        if (!this._biteChecked && progress >= this._biteThreshold) {
          this._biteChecked = true

          // 计算收线速度惩罚：收太快降低中鱼率
          // avgSpeed = 每推进1%进度平均耗时(ms)
          // < 150ms/1% = 极快（惩罚到0.5倍），> 500ms/1% = 慢（无惩罚）
          var avgSpeed = 0
          if (this._reelSpeeds.length > 0) {
            var sum = 0
            for (var i = 0; i < this._reelSpeeds.length; i++) sum += this._reelSpeeds[i]
            avgSpeed = sum / this._reelSpeeds.length
          }
          var speedFactor = 1.0
          if (avgSpeed > 0 && avgSpeed < 500) {
            speedFactor = Math.max(0.5, avgSpeed / 500)  // 最低保留50%概率
          }
          var adjustedChance = this._biteChance * speedFactor

          console.log('[Fishing] 中鱼判定:', {
            distance: this.data.castDistance,
            baseChance: this._biteChance.toFixed(2),
            avgSpeed: Math.round(avgSpeed) + 'ms',
            speedFactor: speedFactor.toFixed(2),
            adjustedChance: adjustedChance.toFixed(2),
            threshold: this._biteThreshold + '%'
          })

          if (Math.random() < adjustedChance) {
            // 中鱼！
            this._onBite()
            return
          }
          // 没中鱼，继续收线到100%
        }

        // 进度满100% -> 收线完毕，没上鱼
        if (progress >= 100 && this.data.state === 'reeling') {
          this._onReelComplete()
        }
      }
    }
    this._lastAngle = angle
  },

  // 收线触摸：结束
  onReelEnd() {
    this._lastAngle = null
    var self = this
    // 延迟停止纺车轮
    if (this._reelStopTimer) { clearTimeout(this._reelStopTimer) }
    this._reelStopTimer = setTimeout(function() {
      self.setData({ reelSpinning: false })
    }, 300)
  },

  // 收线完毕没上鱼
  _onReelComplete() {
    this.setData({
      state: 'escape',
      statusText: '收线完毕，没有鱼上钩\n换个饵再试试？'
    })
    var self = this
    this._resetTimer = setTimeout(function() {
      self._resetToIdle('继续作钓，选饵抛投')
    }, 2000)
  },

  // 没有鱼咬钩
  _onNoBite() {
    this.setData({
      state: 'escape',
      statusText: '没有鱼咬钩...\n换个位置试试？'
    })
    var self = this
    this._resetTimer = setTimeout(function() {
      self._resetToIdle('继续作钓，选饵抛投')
    }, 2000)
  },

  // ===== 上鱼 =====
  _onBite() {
    if (this.data.state !== 'reeling') return

    // 强力震动提示上鱼（用vibrateLong更明显）
    vibrate('long')

    this.setData({
      state: 'bite',
      statusText: '🐟 上鱼了！！\n快猛抬手机刺鱼！'
    })

    wx.startAccelerometer({ interval: 'game' })
    var self = this
    this._accCallback = function(res) {
      if (self.data.state !== 'bite') return
      var acc = Math.sqrt(res.x * res.x + res.y * res.y + res.z * res.z)
      if (acc > ACC.HOOK_MIN) {
        self._handleHook(acc)
      }
    }
    wx.onAccelerometerChange(this._accCallback)

    // 3秒内没刺鱼 -> 鱼跑了
    this._hookTimeout = setTimeout(function() {
      if (self.data.state === 'bite') {
        self._onEscape('反应太慢，鱼跑了！')
      }
    }, 3000)
  },

  // ===== 刺鱼 =====
  _handleHook(acc) {
    wx.stopAccelerometer()
    wx.offAccelerometerChange()
    this._accCallback = null
    if (this._hookTimeout) { clearTimeout(this._hookTimeout); this._hookTimeout = null }

    // 成功率：力度越大越高，50%~95%
    var rate = Math.min(0.95, 0.5 + (acc - ACC.HOOK_MIN) * 0.15)

    if (Math.random() < rate) {
      this._onCatch()
    } else {
      this._onEscape('差一点！鱼挣脱了！')
    }
  },

  // ===== 钓到鱼 =====
  _onCatch() {
    var bait = this.data.selectedBait
    var weightRanges = {
      'common':    [0.5, 2.0],
      'uncommon':  [0.8, 3.5],
      'rare':      [1.0, 4.0],
    }
    var range = weightRanges[bait.rarity] || [0.5, 2.0]
    var weight = (range[0] + Math.random() * (range[1] - range[0])).toFixed(1)

    var fish = {
      id: Date.now(),
      name: bait.fish,
      icon: bait.fishIcon,
      weight: weight,
      bait: bait.name,
      time: this._formatTime(new Date())
    }

    var newCaught = [fish].concat(this.data.caughtFish)
    wx.setStorageSync('fishCaught', newCaught)

    // 钓到鱼震动
    vibrate('heavy')

    this.setData({
      state: 'catch',
      caughtFish: newCaught,
      lastCatch: fish,
      showCatchAnim: true,
      statusText: '钓到一条 ' + fish.name + '！' + fish.weight + ' 斤！'
    })

    var self = this
    this._resetTimer = setTimeout(function() {
      self.setData({ showCatchAnim: false })
      self._resetToIdle('继续作钓，选饵抛投')
    }, 2800)
  },

  // ===== 鱼跑了 =====
  _onEscape(reason) {
    wx.stopAccelerometer()
    wx.offAccelerometerChange()
    this._accCallback = null
    if (this._hookTimeout) { clearTimeout(this._hookTimeout); this._hookTimeout = null }

    this.setData({
      state: 'escape',
      statusText: reason
    })

    var self = this
    this._resetTimer = setTimeout(function() {
      self._resetToIdle('再来一次，选饵抛投')
    }, 2000)
  },

  // ===== 重置到初始状态 =====
  _resetToIdle(text) {
    this.setData({
      state: 'idle',
      castDistance: 0,
      reelProgress: 0,
      reelAngle: 0,
      reelSpinning: false,
      statusText: text,
      lastCatch: null
    })
  },

  // ===== 鱼框 =====
  toggleFishBox() {
    this.setData({ showFishBox: !this.data.showFishBox })
  },

  closeFishBox() {
    this.setData({ showFishBox: false })
  },

  // ===== 一键喂猫 =====
  feedAllToCat() {
    var count = this.data.caughtFish.length
    if (count === 0) return

    var newStock = this.data.fishStock + count
    wx.setStorageSync('fishStock', newStock)
    wx.setStorageSync('fishCaught', [])

    var catLine = CAT_FEED_LINES[Math.floor(Math.random() * CAT_FEED_LINES.length)]

    this.setData({
      fishStock: newStock,
      caughtFish: [],
      showFishBox: false,
      showFeedModal: true,
      feedResult: '小猫收到了 ' + count + ' 条鱼！\n' + catLine + '\n\n鱼库现有 ' + newStock + ' 条鱼'
    })
  },

  closeFeedModal() {
    this.setData({ showFeedModal: false })
  },

  // ===== 工具函数 =====
  _formatTime(date) {
    var m = (date.getMonth() + 1).toString().padStart(2, '0')
    var d = date.getDate().toString().padStart(2, '0')
    var h = date.getHours().toString().padStart(2, '0')
    var min = date.getMinutes().toString().padStart(2, '0')
    return m + '-' + d + ' ' + h + ':' + min
  },

  // 返回首页
  goBack() {
    wx.navigateBack()
  },

  // 阻止冒泡
  noop: function() {}
})
