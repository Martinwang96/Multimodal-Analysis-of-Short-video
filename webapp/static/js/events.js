/* 事件检测页逻辑（函数模块） */
window.Pages = window.Pages || {};
window.Pages.events = async function () {
  try {
    const data = await API.get('/api/events/stats');
    renderEventsPerSource(data.events_per_source);
    renderEventSize(data.size_distribution);
    renderTimeline(data.timeline);
    renderTopics(data.topic_distribution);
    renderSummary(data);
  } catch (e) {
    Util.showError('chart-events-per-source', '加载失败: ' + e.message);
  }

  function renderEventsPerSource(list) {
    if (!list) return;
    Charts.register(Charts.bar(
      document.getElementById('chart-events-per-source'),
      list.map(d => '第' + d.source + '集'), list.map(d => d.event_count),
      { rotate: 50, color: '#D9A441', barMaxWidth: 12 }
    ));
  }
  function renderEventSize(dist) {
    if (!dist) return;
    Charts.register(Charts.bar(
      document.getElementById('chart-event-size'),
      dist.distribution.map(d => d.label), dist.distribution.map(d => d.count),
      { color: '#A98BB9', barMaxWidth: 30 }
    ));
    document.getElementById('event-size-stats').textContent =
      `共 ${dist.total_events} 个事件，平均 ${dist.avg_size} 句/事件，范围 ${dist.min_size} ~ ${dist.max_size} 句`;
  }
  function renderTimeline(timeline) {
    if (!timeline || !timeline.length) return;
    Charts.register(Charts.timeline(document.getElementById('chart-timeline'), timeline));
  }
  function renderTopics(topics) {
    if (!topics) return;
    const pieData = topics.slice(0, 12).map(t => ({ name: t.name, value: t.count }));
    const rest = topics.slice(12).reduce((s, t) => s + t.count, 0);
    if (rest > 0) pieData.push({ name: '其他', value: rest });
    Charts.register(Charts.pie(document.getElementById('chart-topics'), pieData));
  }
  function renderSummary(data) {
    const el = document.getElementById('event-summary');
    const eps = data.events_per_source || [];
    const totalEvents = (data.size_distribution || {}).total_events || 0;
    const maxSource = eps.reduce((a, b) => a.event_count > b.event_count ? a : b, { event_count: 0 });
    const minSource = eps.reduce((a, b) => a.event_count < b.event_count ? a : b, { event_count: Infinity });
    el.innerHTML = `
      <div class="stat-rows">
        <div class="stat-row"><span class="k">事件总数</span><span class="v">${totalEvents}</span></div>
        <div class="stat-row"><span class="k">事件最多的集</span><span class="v">第 ${maxSource.source} 集 · ${maxSource.event_count} 个</span></div>
        <div class="stat-row"><span class="k">事件最少的集</span><span class="v">第 ${minSource.source} 集 · ${minSource.event_count} 个</span></div>
        <div class="stat-row"><span class="k">BERTopic 主题数</span><span class="v">${(data.topic_distribution || []).length}</span></div>
        <div class="stat-row"><span class="k">平均事件大小</span><span class="v">${(data.size_distribution || {}).avg_size || 0} 句</span></div>
      </div>
      <div class="hint">事件 ID 按剧情顺序排列，可在对话浏览页按事件查看完整对白。</div>`;
  }
};
