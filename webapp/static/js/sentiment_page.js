/* 情感分析页逻辑（函数模块） */
window.Pages = window.Pages || {};
window.Pages.sentiment = async function () {
  try {
    const data = await API.get('/api/sentiment', { level: 'all' });
    renderEventLine(data.event || []);
    renderSpeakerLine(data.speaker || []);
    renderDist(data.event || []);
    renderSpeakerAvg(data.speaker || []);
    renderHeatmap(data.speaker || []);
    renderSummary(data);
  } catch (e) {
    Util.showError('chart-event-sentiment', '加载失败: ' + e.message);
  }

  function renderEventLine(events) {
    if (!events.length) return;
    const cats = events.map(e => e.event_id);
    const scores = events.map(e => e.score);
    const chart = Charts.line(
      document.getElementById('chart-event-sentiment'),
      cats, [{ name: '事件情感得分', data: scores }],
      {
        smooth: true, showSymbol: false,
        markLine: { yAxis: 0.5, lineStyle: { color: '#8E8778', type: 'dashed' }, label: { formatter: '中性 0.5', color: '#8E8778' } },
        min: 0, max: 1,
      }
    );
    chart.setOption({
      series: [{
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(217, 164, 65, 0.28)' },
            { offset: 1, color: 'rgba(217, 164, 65, 0)' },
          ]),
        },
      }],
    });
    Charts.register(chart);
  }

  function renderSpeakerLine(speakers) {
    const countMap = {};
    speakers.forEach(s => { countMap[s.speaker] = (countMap[s.speaker] || 0) + 1; });
    const topSpeakers = Object.keys(countMap).sort((a, b) => countMap[b] - countMap[a]).slice(0, 8);
    const eventIds = [...new Set(speakers.map(s => s.event_id))].sort((a, b) => a - b);
    const series = topSpeakers.map(spk => ({
      name: spk,
      data: eventIds.map(eid => {
        const f = speakers.find(s => s.speaker === spk && s.event_id === eid);
        return f ? f.score : null;
      }),
    }));
    Charts.register(Charts.line(
      document.getElementById('chart-speaker-sentiment'),
      eventIds, series,
      { smooth: false, showSymbol: false, legend: true, min: 0, max: 1 }
    ));
  }

  function renderDist(events) {
    let pos = 0, neg = 0;
    events.forEach(e => { if (e.label === 'positive') pos++; else neg++; });
    Charts.register(Charts.pie(
      document.getElementById('chart-dist'),
      [
        { name: '正向事件', value: pos, itemStyle: { color: '#A3B877' } },
        { name: '负向事件', value: neg, itemStyle: { color: '#D4715C' } },
      ],
      { legend: false, radius: ['45%', '70%'], center: ['50%', '50%'] }
    ));
  }

  function renderSpeakerAvg(speakers) {
    const map = {};
    speakers.forEach(s => {
      if (!map[s.speaker]) map[s.speaker] = { sum: 0, count: 0 };
      map[s.speaker].sum += s.score; map[s.speaker].count += 1;
    });
    const arr = Object.keys(map).map(k => ({ speaker: k, avg: map[k].sum / map[k].count }))
      .sort((a, b) => b.avg - a.avg).slice(0, 15);
    const chart = echarts.init(document.getElementById('chart-speaker-avg'));
    chart.setOption({
      tooltip: Charts.baseTooltip(),
      grid: { ...Charts.baseGrid(), left: '18%' },
      xAxis: { type: 'value', ...Charts.baseAxis(), min: 0, max: 1 },
      yAxis: { type: 'category', data: arr.map(a => a.speaker).reverse(), ...Charts.baseAxis() },
      series: [{
        type: 'bar', data: arr.map(a => a.avg).reverse(), barMaxWidth: 20,
        itemStyle: { borderRadius: [0, 3, 3, 0], color: p => p.value >= 0.5 ? '#A3B877' : '#D4715C' },
        label: { show: true, position: 'right', color: '#C6BFB1', fontSize: 11, formatter: p => p.value.toFixed(2) },
      }],
    });
    Charts.register(chart);
  }

  function renderHeatmap(speakers) {
    const countMap = {};
    speakers.forEach(s => { countMap[s.speaker] = (countMap[s.speaker] || 0) + 1; });
    const topSpeakers = Object.keys(countMap).sort((a, b) => countMap[b] - countMap[a]).slice(0, 10);
    const eventIds = [...new Set(speakers.map(s => s.event_id))].sort((a, b) => a - b);
    const speakerIdx = {}; topSpeakers.forEach((s, i) => speakerIdx[s] = i);
    const heatData = [];
    speakers.forEach(s => {
      if (speakerIdx[s.speaker] !== undefined) {
        heatData.push([eventIds.indexOf(s.event_id), speakerIdx[s.speaker], s.score]);
      }
    });
    Charts.register(Charts.heatmap(
      document.getElementById('chart-heatmap'),
      eventIds.map(e => 'E' + e), topSpeakers, heatData,
      { xName: '事件', yName: '角色' }
    ));
  }

  function renderSummary(data) {
    const events = data.event || [];
    const pos = events.filter(e => e.label === 'positive').length;
    const neg = events.length - pos;
    const avgScore = events.length ? (events.reduce((s, e) => s + e.score, 0) / events.length).toFixed(3) : 0;
    const speakers = data.speaker || [];
    const speakerCount = new Set(speakers.map(s => s.speaker)).size;
    document.getElementById('sentiment-summary').innerHTML = `
      <div class="stat-rows">
        <div class="stat-row"><span class="k">分析事件数</span><span class="v">${events.length}</span></div>
        <div class="stat-row"><span class="k">正向事件</span><span class="v text-pos">${pos} · ${(pos / events.length * 100).toFixed(1)}%</span></div>
        <div class="stat-row"><span class="k">负向事件</span><span class="v text-neg">${neg} · ${(neg / events.length * 100).toFixed(1)}%</span></div>
        <div class="stat-row"><span class="k">全剧平均情感得分</span><span class="v">${avgScore}</span></div>
        <div class="stat-row"><span class="k">涉及角色数</span><span class="v">${speakerCount}</span></div>
      </div>
      <div class="hint">本页采用内置中文情感词典打分，为研究方法的轻量复现；与原项目 Erlangshen-Roberta 模型的绝对数值可能存在差异，趋势走向可供参考。</div>`;
  }
};
