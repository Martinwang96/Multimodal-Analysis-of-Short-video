/* ECharts 图表工厂 · 暖黑影院主题（与 main.css 设计系统一致） */
const Charts = {
  /* 电影感低饱和色板：琥珀 / 陶土 / 橄榄 / 灰蓝 / 藕紫 / 蜜黄 / 灰绿 / 暖灰 */
  colors: ['#D9A441', '#C97E5A', '#8FAE6B', '#7C93A8', '#A98BB9',
    '#D4C05B', '#6B9E8F', '#B87A8C', '#9A8C6E', '#5E7FA0',
    '#C4956A', '#7FA87C', '#9487B8', '#B0A458', '#86A0A8'],

  pos: '#A3B877',
  neg: '#D4715C',
  primary: '#D9A441',

  _txt2: '#C6BFB1',
  _txt3: '#8E8778',
  _line: 'rgba(235, 225, 205, 0.18)',
  _split: 'rgba(235, 225, 205, 0.06)',
  _tooltipBg: 'rgba(40, 36, 31, 0.96)',

  baseGrid() {
    return { left: '3%', right: '4%', top: 40, bottom: 50, containLabel: true };
  },

  baseTooltip() {
    return {
      trigger: 'axis',
      backgroundColor: this._tooltipBg,
      borderColor: this._line,
      textStyle: { color: '#F0EBE0', fontSize: 13 },
    };
  },

  baseAxis() {
    return {
      axisLine: { lineStyle: { color: this._line } },
      axisLabel: { color: this._txt3, fontSize: 11 },
      splitLine: { lineStyle: { color: this._split } },
      axisName: { color: this._txt3 },
    };
  },

  // 横向条形图（角色排行）
  horizontalBar(el, categories, values, opts = {}) {
    const chart = echarts.init(el);
    chart.setOption({
      tooltip: { ...this.baseTooltip(), trigger: 'item' },
      grid: { ...this.baseGrid(), left: opts.leftLabelWidth || '15%' },
      xAxis: { type: 'value', ...this.baseAxis() },
      yAxis: {
        type: 'category',
        data: categories,
        ...this.baseAxis(),
        axisLabel: { ...this.baseAxis().axisLabel, fontSize: 12, color: this._txt2 },
        inverse: true,
      },
      series: [{
        type: 'bar',
        data: values,
        barMaxWidth: 20,
        itemStyle: {
          borderRadius: [0, 3, 3, 0],
          color: opts.color || new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#A67C2E' },
            { offset: 1, color: '#D9A441' },
          ]),
        },
        label: { show: true, position: 'right', color: this._txt2, fontSize: 11 },
      }],
    });
    return chart;
  },

  // 纵向柱状图
  bar(el, categories, values, opts = {}) {
    const chart = echarts.init(el);
    chart.setOption({
      tooltip: this.baseTooltip(),
      grid: this.baseGrid(),
      xAxis: {
        type: 'category', data: categories,
        ...this.baseAxis(),
        axisLabel: { ...this.baseAxis().axisLabel, rotate: opts.rotate || 0 },
      },
      yAxis: { type: 'value', ...this.baseAxis() },
      series: [{
        type: 'bar',
        data: values,
        barMaxWidth: opts.barMaxWidth || 26,
        itemStyle: { borderRadius: [3, 3, 0, 0], color: opts.color || this.primary },
      }],
    });
    return chart;
  },

  // 折线图
  line(el, categories, seriesData, opts = {}) {
    const chart = echarts.init(el);
    const series = seriesData.map((s, i) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: opts.smooth !== false,
      symbol: opts.showSymbol === false ? 'none' : 'circle',
      symbolSize: 5,
      showSymbol: opts.showSymbol === false ? false : true,
      lineStyle: { width: 2 },
      itemStyle: { color: this.colors[i % this.colors.length] },
    }));

    const markLines = [];
    if (opts.markLine) markLines.push(opts.markLine);

    chart.setOption({
      color: this.colors,
      tooltip: this.baseTooltip(),
      legend: opts.legend ? {
        data: seriesData.map(s => s.name),
        textStyle: { color: this._txt2, fontSize: 12 },
        top: 5,
        type: 'scroll',
      } : undefined,
      grid: this.baseGrid(),
      xAxis: {
        type: 'category', data: categories,
        ...this.baseAxis(),
        axisLabel: { ...this.baseAxis().axisLabel, rotate: opts.xRotate || 0 },
      },
      yAxis: { type: 'value', ...this.baseAxis(), min: opts.min, max: opts.max },
      series: series.map(s => ({
        ...s,
        markLine: markLines.length ? { silent: true, data: markLines } : undefined,
      })),
    });
    return chart;
  },

  // 饼图/环形图
  pie(el, data, opts = {}) {
    const chart = echarts.init(el);
    chart.setOption({
      color: this.colors,
      tooltip: {
        trigger: 'item',
        backgroundColor: this._tooltipBg,
        borderColor: this._line,
        textStyle: { color: '#F0EBE0' },
        formatter: '{b}: {c} ({d}%)',
      },
      legend: opts.legend === false ? undefined : {
        type: 'scroll',
        orient: 'vertical',
        right: 10,
        top: 'center',
        textStyle: { color: this._txt2, fontSize: 12 },
      },
      series: [{
        type: 'pie',
        radius: opts.radius || ['40%', '70%'],
        center: opts.center || ['40%', '50%'],
        data: data,
        label: { color: this._txt2, fontSize: 12 },
        itemStyle: { borderColor: '#28241F', borderWidth: 2 },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
      }],
    });
    return chart;
  },

  // 词云
  wordcloud(el, data) {
    const chart = echarts.init(el);
    chart.setOption({
      tooltip: {
        backgroundColor: this._tooltipBg,
        borderColor: this._line,
        textStyle: { color: '#F0EBE0' },
      },
      series: [{
        type: 'wordCloud',
        shape: 'circle',
        left: 'center', top: 'center',
        width: '90%', height: '90%',
        sizeRange: [14, 58],
        rotationRange: [-30, 30],
        rotationStep: 30,
        gridSize: 8,
        drawOutOfBound: false,
        textStyle: {
          fontFamily: "'Noto Serif SC', 'Noto Sans SC', serif",
          fontWeight: 600,
          color: function () {
            const cs = ['#D9A441', '#C97E5A', '#8FAE6B', '#A98BB9',
              '#D4C05B', '#7C93A8', '#E8BC64', '#B87A8C'];
            return cs[Math.floor(Math.random() * cs.length)];
          },
        },
        emphasis: { textStyle: { shadowBlur: 12, shadowColor: 'rgba(217, 164, 65, 0.6)' } },
        data: data,
      }],
    });
    return chart;
  },

  // 热力图
  heatmap(el, xAxisData, yAxisData, data, opts = {}) {
    const chart = echarts.init(el);
    const values = data.map(d => d[2]);
    const min = Math.min(...values), max = Math.max(...values);
    chart.setOption({
      tooltip: {
        backgroundColor: this._tooltipBg,
        borderColor: this._line,
        textStyle: { color: '#F0EBE0' },
        formatter: p => `${opts.xName || ''} ${p.value[0]}<br/>${opts.yName || ''} ${p.value[1]}<br/>值: ${p.value[2]}`,
      },
      grid: { ...this.baseGrid(), height: '70%' },
      xAxis: {
        type: 'category', data: xAxisData, splitArea: { show: true },
        ...this.baseAxis(),
        axisLabel: { ...this.baseAxis().axisLabel, rotate: 45 },
      },
      yAxis: {
        type: 'category', data: yAxisData, splitArea: { show: true },
        ...this.baseAxis(),
        axisLabel: { ...this.baseAxis().axisLabel, color: this._txt2 },
      },
      visualMap: {
        min, max, calculable: true,
        orient: 'horizontal', left: 'center', bottom: 5,
        textStyle: { color: this._txt3 },
        /* 陶土红（负） → 暖黑中点 → 琥珀（正） */
        inRange: { color: ['#D4715C', '#5A4A38', '#D9A441', '#E8BC64'] },
      },
      series: [{
        type: 'heatmap', data: data,
        label: { show: false },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
      }],
    });
    return chart;
  },

  // 事件时间线（自定义 series）
  timeline(el, data, opts = {}) {
    const chart = echarts.init(el);
    const colorByValue = v => {
      if (v >= 30) return '#C97E5A';
      if (v >= 15) return '#D9A441';
      if (v >= 8) return '#A98BB9';
      return '#7C93A8';
    };
    chart.setOption({
      tooltip: {
        backgroundColor: this._tooltipBg,
        borderColor: this._line,
        textStyle: { color: '#F0EBE0' },
        formatter: p => {
          const d = data[p.dataIndex];
          return `事件 ${d.event_id}<br/>集: ${d.primary_source}<br/>对白数: ${d.line_count}<br/>角色数: ${d.speaker_count}`;
        },
      },
      grid: { ...this.baseGrid(), top: 30, bottom: 60 },
      xAxis: {
        type: 'category',
        data: data.map(d => `E${d.event_id}`),
        ...this.baseAxis(),
        axisLabel: { show: false },
      },
      yAxis: { type: 'value', ...this.baseAxis(), name: '对白数' },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', start: 0, end: 100, height: 18, bottom: 15,
          textStyle: { color: this._txt3 },
          borderColor: this._line,
          fillerColor: 'rgba(217, 164, 65, 0.12)',
          handleStyle: { color: '#D9A441' } },
      ],
      series: [{
        type: 'custom',
        renderItem: (params, api) => {
          const idx = api.value(0);
          const val = api.value(1);
          const point = api.coord([idx, val]);
          return {
            type: 'rect',
            shape: { x: point[0] - 2, y: point[1], width: 4, height: params.coordSys.y - point[1] },
            style: { fill: colorByValue(val) },
          };
        },
        data: data.map((d, i) => [i, d.line_count]),
        encode: { x: 0, y: 1 },
      }],
    });
    return chart;
  },

  // 实例注册与响应式
  _instances: [],
  register(chart) {
    this._instances.push(chart);
    return chart;
  },
  resizeAll() {
    this._instances.forEach(c => c && c.resize());
  },
};

window.addEventListener('resize', () => Charts.resizeAll());
