/* API 客户端 - 双模式数据访问
 * Flask 模式: 调用 /api/* 接口
 * 静态模式: 从 window.__DATA__ 读取预计算数据（前端筛选分页）
 */
const API = {
  isStatic: typeof window.__DATA__ !== 'undefined',

  async get(endpoint, params = {}) {
    if (this.isStatic) {
      return this._staticGet(endpoint, params);
    }
    const url = this._buildUrl(endpoint, params);
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async post(endpoint, body) {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  _buildUrl(endpoint, params) {
    const sp = new URLSearchParams();
    Object.keys(params).forEach(k => {
      if (params[k] !== null && params[k] !== undefined && params[k] !== '') {
        sp.set(k, params[k]);
      }
    });
    const qs = sp.toString();
    return qs ? `${endpoint}?${qs}` : endpoint;
  },

  _staticGet(endpoint, params) {
    const D = window.__DATA__;
    if (endpoint.startsWith('/api/overview')) return Promise.resolve(D.overview);
    if (endpoint.startsWith('/api/speakers')) return Promise.resolve(D.speakers);
    if (endpoint.startsWith('/api/events/stats')) return Promise.resolve(D.eventsStats);
    if (endpoint.startsWith('/api/events')) return Promise.resolve(D.events);
    if (endpoint.startsWith('/api/sources')) return Promise.resolve(D.sources);
    if (endpoint.startsWith('/api/text/stats')) return Promise.resolve(D.textStats);
    if (endpoint.startsWith('/api/sentiment')) {
      const level = params.level || 'all';
      if (level === 'all') return Promise.resolve(D.sentiment);
      return Promise.resolve(D.sentiment[level] || []);
    }
    if (endpoint.startsWith('/api/dialogues')) {
      return Promise.resolve(this._filterDialogues(params));
    }
    return Promise.reject(new Error(`静态模式未知端点: ${endpoint}`));
  },

  _filterDialogues(params) {
    let items = (window.__DATA__.allDialogues || []).slice();
    if (params.event_id) items = items.filter(d => String(d.event_id) === String(params.event_id));
    if (params.source) items = items.filter(d => String(d.source) === String(params.source));
    if (params.speaker) items = items.filter(d => d.speaker === params.speaker);
    if (params.keyword) items = items.filter(d => d.text.includes(params.keyword));

    const total = items.length;
    const size = Math.min(parseInt(params.size) || 50, 200);
    const page = parseInt(params.page) || 1;
    const start = (page - 1) * size;
    const pageItems = items.slice(start, start + size);
    const pages = total > 0 ? Math.ceil(total / size) : 0;

    const eventSet = new Set(items.map(d => d.event_id));
    const speakerSet = new Set(items.map(d => d.speaker));

    return {
      items: pageItems,
      total,
      page,
      pages,
      size,
      involved_events: eventSet.size,
      involved_speakers: speakerSet.size,
    };
  },
};

/* 通用工具 */
const Util = {
  // 说话人 -> 颜色（基于名字哈希，与 Charts 色板一致）
  speakerColor(name) {
    const palette = ['#D9A441', '#C97E5A', '#8FAE6B', '#7C93A8', '#A98BB9',
      '#D4C05B', '#6B9E8F', '#B87A8C', '#C4956A', '#5E7FA0'];
    let h = 0;
    for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
    return palette[Math.abs(h) % palette.length];
  },
  // 防抖
  debounce(fn, wait = 300) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  },
  // 显示错误
  showError(container, msg) {
    if (typeof container === 'string') container = document.getElementById(container);
    if (container) container.innerHTML = `<div class="error-msg">${msg}</div>`;
  },
  // 显示加载
  showLoading(container) {
    if (typeof container === 'string') container = document.getElementById(container);
    if (container) container.innerHTML = '<div class="loading">加载中...</div>';
  },
};
