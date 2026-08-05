"""Flask Web 应用入口。

提供：
- 5 个页面路由（概览/文本分析/事件检测/对话浏览/情感分析）
- 8 个 REST API 端点（数据查询与情感分析）
- CSV 上传接口（加载同格式自定义数据）

运行方式：
    cd webapp
    python app.py
然后浏览器访问 http://127.0.0.1:5000
"""
import os
import tempfile

from flask import Flask, render_template, jsonify, request, send_from_directory, abort

from config import (
    EVENTS_CSV, RAW_CSV, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE,
    MAX_UPLOAD_SIZE, ALLOWED_EXTENSIONS,
)
from services.data_service import get_service as get_data_service
from services.text_service import get_service as get_text_service
from services.sentiment_service import get_service as get_sentiment_service
from services.event_service import get_service as get_event_service

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


# ==================== 页面路由 ====================

@app.route("/")
def page_overview():
    return render_template("overview.html", active_page="overview")


@app.route("/text")
def page_text():
    return render_template("text.html", active_page="text")


@app.route("/events")
def page_events():
    return render_template("events.html", active_page="events")


@app.route("/browser")
def page_browser():
    return render_template("browser.html", active_page="browser")


@app.route("/sentiment")
def page_sentiment():
    return render_template("sentiment.html", active_page="sentiment")


# ==================== REST API ====================

@app.route("/api/overview")
def api_overview():
    """项目概览指标。"""
    try:
        return jsonify(get_data_service().get_overview())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/speakers")
def api_speakers():
    """角色列表及台词统计。"""
    try:
        return jsonify(get_data_service().get_speakers())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dialogues")
def api_dialogues():
    """对话查询（筛选 + 分页）。

    参数: event_id, source, speaker, keyword, page, size
    """
    try:
        event_id = request.args.get("event_id", type=int)
        source = request.args.get("source", type=int)
        speaker = request.args.get("speaker", type=str)
        keyword = request.args.get("keyword", type=str)
        page = request.args.get("page", default=1, type=int)
        size = request.args.get("size", default=DEFAULT_PAGE_SIZE, type=int)
        result = get_data_service().query_dialogues(
            event_id=event_id, source=source, speaker=speaker,
            keyword=keyword, page=page, size=size,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/events")
def api_events():
    """事件汇总列表。"""
    try:
        return jsonify(get_data_service().get_events_summary())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/events/stats")
def api_events_stats():
    """事件统计：每集事件数、大小分布、主题分布、时间线。"""
    try:
        es = get_event_service()
        return jsonify({
            "events_per_source": es.get_events_per_source(),
            "size_distribution": es.get_event_size_distribution(),
            "topic_distribution": es.get_topic_distribution(),
            "timeline": es.get_event_timeline(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sources")
def api_sources():
    """集(source)列表。"""
    try:
        return jsonify({
            "sources": get_data_service().get_source_list(),
            "speakers": get_data_service().get_speaker_list(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/text/stats")
def api_text_stats():
    """文本统计：词频 Top N + 词云数据 + 字数分布。"""
    try:
        limit = request.args.get("limit", default=20, type=int)
        speaker = request.args.get("speaker", type=str)
        ts = get_text_service()
        result = ts.get_word_frequency(limit=limit)
        result["distribution"] = ts.get_text_distribution()
        if speaker:
            result["speaker_words"] = ts.get_speaker_word_frequency(speaker)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sentiment")
def api_sentiment():
    """情感分析（词典法）。

    参数:
        level: sentence | event | speaker | all（默认 all）
    """
    try:
        level = request.args.get("level", default="all", type=str)
        ss = get_sentiment_service()
        ds = get_data_service()
        df = ds.events_df

        if level == "all":
            sentences, events, speakers = ss.analyze_all(df)
            return jsonify({
                "sentence": sentences,
                "event": events,
                "speaker": speakers,
            })
        elif level == "sentence":
            sentences, _, _ = ss.analyze_all(df)
            return jsonify(sentences)
        elif level == "event":
            _, events, _ = ss.analyze_all(df)
            return jsonify(events)
        elif level == "speaker":
            _, _, speakers = ss.analyze_all(df)
            return jsonify(speakers)
        else:
            return jsonify({"error": f"未知 level: {level}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sentiment/score", methods=["POST"])
def api_sentiment_score():
    """对单条文本实时打分（POST body: {"text": "..."}）。"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        text = data.get("text", "")
        return jsonify(get_sentiment_service().score_text(text))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== CSV 上传 ====================

@app.route("/api/upload", methods=["POST"])
def api_upload():
    """上传同格式 CSV 替换当前数据集。

    要求 CSV 至少包含列：说话人, 文本内容, source
    若含 事件ID_Hybrid_V5 则视为事件结果格式。
    """
    if "file" not in request.files:
        return jsonify({"error": "未提供文件"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "文件名为空"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"仅支持 CSV 文件，收到 {ext}"}), 400

    # 保存到临时文件并校验
    import pandas as pd
    tmp_path = os.path.join(tempfile.gettempdir(), "upload_check.csv")
    file.save(tmp_path)
    try:
        df = pd.read_csv(tmp_path)
        required = {"说话人", "文本内容", "source"}
        if not required.issubset(set(df.columns)):
            missing = required - set(df.columns)
            return jsonify({"error": f"CSV 缺少必要列: {missing}"}), 400
    except Exception as e:
        return jsonify({"error": f"CSV 解析失败: {e}"}), 400

    # 校验通过，替换数据文件并重置服务单例
    import shutil
    if "事件ID_Hybrid_V5" in df.columns:
        target = str(EVENTS_CSV)
    else:
        target = str(RAW_CSV)
    shutil.move(tmp_path, target)

    # 重置所有服务单例以重新加载
    from services import data_service, text_service, sentiment_service, event_service
    data_service._service = None
    text_service._service = None
    sentiment_service._service = None
    event_service._service = None

    return jsonify({
        "message": "上传成功，数据已更新",
        "target": os.path.basename(target),
        "rows": len(df),
    })


# ==================== 静态文件 ====================

@app.route("/lib/<path:filename>")
def serve_lib(filename):
    """提供 static/lib 下的第三方库文件。"""
    return send_from_directory("static/lib", filename)


@app.route("/lexicon/<path:filename>")
def serve_lexicon(filename):
    """提供情感词典 JSON（供前端客户端打分使用）。"""
    return send_from_directory("lexicon", filename)


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "接口不存在"}), 404
    return render_template("overview.html", active_page="overview"), 404


@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "服务器内部错误"}), 500
    return jsonify({"error": "服务器内部错误"}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("《反方向的钟》多模态分析 Web 应用")
    print("访问 http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=True)
