/* 文本分析页逻辑（函数模块） */
window.Pages = window.Pages || {};
window.Pages.text = async function () {
  try {
    const [speakers, textStats] = await Promise.all([
      API.get('/api/speakers'),
      API.get('/api/text/stats', { limit: 20 }),
    ]);
    renderLineCount(speakers);
    renderLineChars(speakers);
    renderWordcloud(textStats.wordcloud_words);
    renderTopWords(textStats.top_words);
    renderCharDist(textStats.distribution);
  } catch (e) {
    Util.showError('chart-line-count', '加载失败: ' + e.message);
  }

  function renderLineCount(speakers) {
    const top = speakers.slice(0, 15);
    Charts.register(Charts.horizontalBar(
      document.getElementById('chart-line-count'),
      top.map(s => s.speaker), top.map(s => s.line_count),
      { leftLabelWidth: '18%' }
    ));
  }
  function renderLineChars(speakers) {
    const sorted = [...speakers].sort((a, b) => b.total_chars - a.total_chars).slice(0, 15);
    Charts.register(Charts.horizontalBar(
      document.getElementById('chart-line-chars'),
      sorted.map(s => s.speaker), sorted.map(s => s.total_chars),
      {
        leftLabelWidth: '18%',
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#9E5F41' }, { offset: 1, color: '#C97E5A' },
        ]),
      }
    ));
  }
  function renderWordcloud(words) {
    if (!words || !words.length) return;
    Charts.register(Charts.wordcloud(document.getElementById('chart-wordcloud'), words));
  }
  function renderTopWords(topWords) {
    if (!topWords) return;
    Charts.register(Charts.bar(
      document.getElementById('chart-top-words'),
      topWords.map(w => w.word), topWords.map(w => w.count),
      { rotate: 40, color: '#7C93A8', barMaxWidth: 24 }
    ));
  }
  function renderCharDist(dist) {
    if (!dist || !dist.char_distribution) return;
    Charts.register(Charts.bar(
      document.getElementById('chart-char-dist'),
      dist.char_distribution.map(d => d.label), dist.char_distribution.map(d => d.count),
      { color: '#8FAE6B', barMaxWidth: 30 }
    ));
    const s = dist.char_stats;
    document.getElementById('char-stats').textContent =
      `字数范围: ${s.min} ~ ${s.max}，平均 ${s.avg} 字/句；词数平均 ${dist.word_stats.avg} 词/句`;
  }
};
