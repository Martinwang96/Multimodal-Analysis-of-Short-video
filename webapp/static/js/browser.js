/* 对话浏览页逻辑（函数模块） */
window.Pages = window.Pages || {};
window.Pages.browser = function () {
  if (!window._browserState) {
    window._browserState = {
      page: 1, size: 50, initialized: false,
    };
  }
  const state = window._browserState;

  const Browser = {
    async init() {
      if (!state.initialized) {
        try {
          const opts = await API.get('/api/sources');
          this.fillFilters(opts.sources || [], opts.speakers || []);
          this.bindEvents();
          state.initialized = true;
        } catch (e) {
          Util.showError('dialogue-container', '初始化失败: ' + e.message);
          return;
        }
      }
      await this.load();
    },

    fillFilters(sources, speakers) {
      const srcSel = document.getElementById('filter-source');
      const spkSel = document.getElementById('filter-speaker');
      // 保留首个占位项，清空其余
      while (srcSel.options.length > 1) srcSel.remove(1);
      while (spkSel.options.length > 1) spkSel.remove(1);
      sources.forEach(s => {
        const o = document.createElement('option');
        o.value = s; o.textContent = '第' + s + '集';
        srcSel.appendChild(o);
      });
      speakers.forEach(s => {
        const o = document.createElement('option');
        o.value = s; o.textContent = s;
        spkSel.appendChild(o);
      });
    },

    bindEvents() {
      document.getElementById('btn-search').addEventListener('click', () => {
        state.page = 1; this.load();
      });
      document.getElementById('btn-reset').addEventListener('click', () => {
        document.getElementById('filter-source').value = '';
        document.getElementById('filter-event').value = '';
        document.getElementById('filter-speaker').value = '';
        document.getElementById('filter-keyword').value = '';
        state.page = 1; this.load();
      });
      document.getElementById('filter-keyword').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { state.page = 1; this.load(); }
      });
    },

    getParams() {
      return {
        source: document.getElementById('filter-source').value || null,
        event_id: document.getElementById('filter-event').value || null,
        speaker: document.getElementById('filter-speaker').value || null,
        keyword: document.getElementById('filter-keyword').value || null,
        page: state.page, size: state.size,
      };
    },

    async load() {
      const container = document.getElementById('dialogue-container');
      Util.showLoading(container);
      try {
        const data = await API.get('/api/dialogues', this.getParams());
        this.render(data);
      } catch (e) {
        Util.showError(container, '加载失败: ' + e.message);
      }
    },

    render(data) {
      const container = document.getElementById('dialogue-container');
      document.getElementById('result-summary').textContent =
        `共 ${data.total} 条 · 涉及 ${data.involved_events} 个事件 / ${data.involved_speakers} 个角色 · 第 ${data.page}/${data.pages || 1} 页`;
      if (!data.items || !data.items.length) {
        container.innerHTML = '<div class="empty">无匹配对话</div>';
        document.getElementById('pagination').innerHTML = '';
        return;
      }
      let html = '<div class="dialogue-list">';
      data.items.forEach(item => {
        const color = Util.speakerColor(item.speaker);
        if (item.is_new_event) {
          html += `<div class="event-break"><span class="event-break-label">事件 ${item.event_id} · 第${item.source}集</span></div>`;
        }
        html += `
          <div class="dialogue-item">
            <div class="speaker-dot" style="background:${color};"></div>
            <div style="flex:1;">
              <div class="dialogue-meta">
                <span style="color:${color}; font-weight:600;">${item.speaker}</span>
                · 第${item.source}集 · 事件${item.event_id} · 行${item.row_no}
              </div>
              <div class="dialogue-text">${this.escape(item.text)}</div>
            </div>
          </div>`;
      });
      html += '</div>';
      container.innerHTML = html;
      this.renderPagination(data);
    },

    renderPagination(data) {
      const el = document.getElementById('pagination');
      if (data.pages <= 1) { el.innerHTML = ''; return; }
      let html = '';
      html += `<button ${data.page <= 1 ? 'disabled' : ''} data-p="${data.page - 1}">上一页</button>`;
      let start = Math.max(1, data.page - 4);
      let end = Math.min(data.pages, start + 8);
      start = Math.max(1, end - 8);
      if (start > 1) html += `<button data-p="1">1</button><span class="text-muted">…</span>`;
      for (let i = start; i <= end; i++) {
        html += `<button class="${i === data.page ? 'active' : ''}" data-p="${i}">${i}</button>`;
      }
      if (end < data.pages) html += `<span class="text-muted">…</span><button data-p="${data.pages}">${data.pages}</button>`;
      html += `<button ${data.page >= data.pages ? 'disabled' : ''} data-p="${data.page + 1}">下一页</button>`;
      el.innerHTML = html;
      el.querySelectorAll('button[data-p]').forEach(btn => {
        btn.addEventListener('click', () => {
          if (btn.disabled) return;
          state.page = parseInt(btn.dataset.p);
          this.load();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
      });
    },

    escape(s) {
      return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[c]));
    },
  };

  Browser.init();
};
