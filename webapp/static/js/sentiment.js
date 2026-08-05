/* 客户端情感打分 - 与 Python 端共享词典与算法约定
 * 子串匹配词典词 → 加权统计 → 正向概率作为得分
 * 静态模式从 window.__DATA__.lexicon 加载词典；
 * Flask 模式可通过 fetch 词典或使用后端预计算结果。
 */
const Sentiment = {
  lexicon: { positive: {}, negative: {} },
  threshold: 0.5,
  loaded: false,

  async init() {
    if (this.loaded) return;
    // 静态模式：从内嵌数据加载
    if (typeof window.__DATA__ !== 'undefined' && window.__DATA__.lexicon) {
      this.lexicon = window.__DATA__.lexicon;
      this.loaded = true;
      return;
    }
    // Flask 模式：从静态文件加载词典
    try {
      const res = await fetch('/lexicon/sentiment_words.json');
      if (res.ok) {
        this.lexicon = await res.json();
        this.loaded = true;
      }
    } catch (e) {
      console.warn('情感词典加载失败，客户端打分不可用', e);
    }
  },

  scoreText(text) {
    if (!text || typeof text !== 'string' || text.length < 1) {
      return { score: this.threshold, label: 'neutral', pos: 0, neg: 0 };
    }
    let pos = 0, neg = 0;
    const posWords = this.lexicon.positive || {};
    const negWords = this.lexicon.negative || {};

    // 子串匹配（轻量方案，比 Python 端 jieba 分词略粗）
    for (const w in posWords) {
      if (w && text.includes(w)) pos += Number(posWords[w]) || 1;
    }
    for (const w in negWords) {
      if (w && text.includes(w)) neg += Number(negWords[w]) || 1;
    }

    const total = pos + neg;
    const score = total <= 0 ? this.threshold : pos / total;
    return {
      score: Math.round(score * 10000) / 10000,
      label: score >= this.threshold ? 'positive' : 'negative',
      pos: pos,
      neg: neg,
    };
  },

  scoreBatch(texts) {
    return texts.map(t => this.scoreText(t));
  },
};
