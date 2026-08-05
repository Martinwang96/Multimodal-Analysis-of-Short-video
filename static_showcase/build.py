"""静态展示页生成器。

导入 webapp 服务层预计算全部数据，读取共享 CSS/JS 与页面模板，
组装成自包含的单文件 static_showcase/index.html（双击即开，ECharts 经 CDN 加载）。

运行方式：
    cd static_showcase
    python build.py
输出：static_showcase/index.html
"""
import json
import os
import re
import sys
from pathlib import Path

# 将 webapp 目录加入搜索路径以复用服务层
WEBAPP_DIR = Path(__file__).resolve().parent.parent / "webapp"
sys.path.insert(0, str(WEBAPP_DIR))

from services.data_service import get_service as get_data_service
from services.text_service import get_service as get_text_service
from services.sentiment_service import get_service as get_sentiment_service
from services.event_service import get_service as get_event_service

# 强制重载：避免 __pycache__ 缓存上次 import 的旧代码导致 build 看不到最新修改
import importlib
import services.data_service as _ds
import services.text_service as _ts
import services.sentiment_service as _ss
import services.event_service as _es
importlib.reload(_ds)
importlib.reload(_ts)
importlib.reload(_ss)
importlib.reload(_es)
get_data_service = _ds.get_service
get_text_service = _ts.get_service
get_sentiment_service = _ss.get_service
get_event_service = _es.get_service

# 资源目录
STATIC_DIR = WEBAPP_DIR / "static"
TEMPLATES_DIR = WEBAPP_DIR / "templates"
LEXICON_PATH = WEBAPP_DIR / "lexicon" / "sentiment_words.json"
OUTPUT = Path(__file__).resolve().parent / "index.html"


def to_jsonable(obj):
    """递归转换 numpy 类型为原生 Python 类型。"""
    import numpy as np
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [to_jsonable(v) for v in obj.tolist()]
    return obj


def collect_data():
    """调用各服务预计算全部数据。"""
    print("预计算数据中...")
    ds = get_data_service()
    ts = get_text_service()
    ss = get_sentiment_service()
    es = get_event_service()

    # 全部对话（供静态页前端筛选分页）
    df = ds.events_df
    all_dialogues = []
    for _, row in df.iterrows():
        all_dialogues.append({
            "row_no": int(row["原始行号"]),
            "speaker": str(row["说话人"]),
            "text": str(row["文本内容"]),
            "source": int(row["source"]),
            "event_id": int(row["事件ID_Hybrid_V5"]),
            "topic_id": int(row["BERTopic主题ID_Erlangshen"]),
            "is_new_event": bool(row["是否为新事件开始_Hybrid_V5"]),
        })

    # 情感分析三层级
    sentences, events_sent, speakers_sent = ss.analyze_all(df)

    # 词典
    with open(LEXICON_PATH, "r", encoding="utf-8") as f:
        lexicon = json.load(f)

    # 文本统计：词频 + 字数/词数分布（与 Flask /api/text/stats 结构一致）
    _text = ts.get_word_frequency(limit=20)
    _text["distribution"] = ts.get_text_distribution()

    data = {
        "overview": ds.get_overview(),
        "speakers": ds.get_speakers(),
        "events": ds.get_events_summary(),
        "eventsStats": {
            "events_per_source": es.get_events_per_source(),
            "size_distribution": es.get_event_size_distribution(),
            "topic_distribution": es.get_topic_distribution(),
            "timeline": es.get_event_timeline(),
        },
        "sources": {
            "sources": ds.get_source_list(),
            "speakers": ds.get_speaker_list(),
        },
        "textStats": _text,
        "sentiment": {
            "sentence": sentences,
            "event": events_sent,
            "speaker": speakers_sent,
        },
        "allDialogues": all_dialogues,
        "lexicon": lexicon,
    }
    print(f"  对白 {len(all_dialogues)} 条，事件 {len(data['events'])} 个，"
          f"情感事件 {len(events_sent)} 个")
    return to_jsonable(data)


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_content(template_name):
    """从 Flask 模板提取 {% block content %} 内容（纯 HTML）。"""
    content = read_file(TEMPLATES_DIR / template_name)
    m = re.search(r"{% block content %}(.*?){% endblock %}", content, re.DOTALL)
    return m.group(1).strip() if m else ""


# 单页路由 JS
ROUTER_JS = r"""
/* 静态页单页路由 */
const Router = {
  init() {
    const name = (location.hash || '#overview').slice(1);
    this.show(name);
    window.addEventListener('hashchange', () => {
      this.show((location.hash || '#overview').slice(1));
    });
  },
  show(name) {
    const valid = ['overview','text','events','browser','sentiment'];
    if (valid.indexOf(name) < 0) name = 'overview';
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const sec = document.getElementById('page-' + name);
    if (sec) sec.style.display = 'block';
    document.querySelectorAll('.nav-link').forEach(a => {
      a.classList.toggle('active', a.getAttribute('href') === '#' + name);
    });
    // 销毁旧图表实例，避免重复渲染与 resize 报错
    if (window.Charts && Charts._instances) {
      Charts._instances.forEach(c => { try { c.dispose(); } catch (e) {} });
      Charts._instances = [];
    }
    // 调用对应页面渲染函数
    if (window.Pages && window.Pages[name]) {
      try { window.Pages[name](); } catch (e) { console.error('页面渲染错误:', e); }
    }
    window.scrollTo(0, 0);
  }
};
document.addEventListener('DOMContentLoaded', () => Router.init());
"""


def build():
    data = collect_data()

    # 读取共享资源
    css = read_file(STATIC_DIR / "css" / "main.css")
    api_js = read_file(STATIC_DIR / "js" / "api.js")
    charts_js = read_file(STATIC_DIR / "js" / "charts.js")
    sentiment_js = read_file(STATIC_DIR / "js" / "sentiment.js")
    page_js = {
        "overview": read_file(STATIC_DIR / "js" / "overview.js"),
        "text": read_file(STATIC_DIR / "js" / "text.js"),
        "events": read_file(STATIC_DIR / "js" / "events.js"),
        "browser": read_file(STATIC_DIR / "js" / "browser.js"),
        "sentiment": read_file(STATIC_DIR / "js" / "sentiment_page.js"),
    }

    # 提取各页面 content
    contents = {
        "overview": extract_content("overview.html"),
        "text": extract_content("text.html"),
        "events": extract_content("events.html"),
        "browser": extract_content("browser.html"),
        "sentiment": extract_content("sentiment.html"),
    }

    # 静态页为 hash 单页路由：将模板中的 Flask 路由链接替换为 hash 链接
    for name, html in contents.items():
        for route in ["text", "events", "browser", "sentiment"]:
            html = html.replace(f'href="/{route}"', f'href="#{route}"')
        html = html.replace('href="/"', 'href="#overview"')
        contents[name] = html

    # 组装页面 section
    sections = []
    for name in ["overview", "text", "events", "browser", "sentiment"]:
        style = "" if name == "overview" else ' style="display:none"'
        sections.append(f'<section id="page-{name}" class="page"{style}>\n{contents[name]}\n</section>')

    data_json = json.dumps(data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>《反方向的钟》多模态分析 · 静态展示</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='44' fill='none' stroke='%23D9A441' stroke-width='7'/><path d='M50 26v24l17 10' fill='none' stroke='%23D9A441' stroke-width='7' stroke-linecap='round'/></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/echarts-wordcloud@2.1.0/dist/echarts-wordcloud.min.js"></script>
  <style>
{css}
.page {{ display: none; }}
  </style>
</head>
<body>
  <nav class="topnav">
    <a href="#overview" class="brand">
      <span class="brand-title">反方向的钟</span>
      <span class="brand-sub">多模态叙事分析</span>
    </a>
    <div class="nav-links">
      <a href="#overview" class="nav-link active">概览</a>
      <a href="#text" class="nav-link">文本分析</a>
      <a href="#events" class="nav-link">事件检测</a>
      <a href="#browser" class="nav-link">对话浏览</a>
      <a href="#sentiment" class="nav-link">情感分析</a>
    </div>
    <div class="mode-badge">静态展示</div>
  </nav>

  <main class="content">
{chr(10).join(sections)}
  </main>

  <footer class="footer">
    <span>短剧文本特征研究 · 以《反方向的钟》为例</span>
    <span class="footer-sep">·</span>
    <span>转写 — 事件检测 — 情感分析 — 可视化</span>
  </footer>

  <script>window.__DATA__ = {data_json};</script>
  <script>
{api_js}
  </script>
  <script>
{charts_js}
  </script>
  <script>
{sentiment_js}
  </script>
  <script>
{page_js['overview']}
{page_js['text']}
{page_js['events']}
{page_js['browser']}
{page_js['sentiment']}
  </script>
  <script>
{ROUTER_JS}
  </script>
</body>
</html>
"""

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"\n生成完成: {OUTPUT}")
    print(f"文件大小: {size_kb:.1f} KB")
    print("双击 index.html 即可在浏览器打开（需联网加载 ECharts CDN）。")


if __name__ == "__main__":
    build()
