from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


SHARE_ID = "wbce065332f008a5d"
RAW_HTML_NAME = f"thread_{SHARE_ID}.html"
PAIRS_JSON_NAME = "doubao_pairs_extracted.json"
SUMMARY_JSON_NAME = f"doubao_thread_{SHARE_ID}_summary.json"
SUMMARY_HTML_NAME = f"doubao_thread_{SHARE_ID}_summary.html"
SUMMARY_PDF_NAME = f"doubao_thread_{SHARE_ID}_summary.pdf"
SUMMARY_CHROME_PDF_NAME = f"doubao_thread_{SHARE_ID}_summary.chrome.pdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate Doubao thread summary artifacts.")
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory that contains the raw Doubao thread HTML.",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Only regenerate JSON/HTML, skip browser PDF export.",
    )
    return parser.parse_args()


def parse_json_maybe(value):
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def load_message_payload(raw_html_path: Path) -> dict:
    text = raw_html_path.read_text(encoding="utf-8")
    match = re.search(
        r'<script[^>]*data-fn-name="r"[^>]*data-fn-args="([^"]*)"',
        text,
        re.S,
    )
    if not match:
        raise RuntimeError("Failed to find message payload in thread HTML.")
    data = json.loads(html.unescape(match.group(1)))
    return data[2]


def extract_text(message: dict) -> str:
    parts: list[str] = []
    for block in message.get("content_block") or []:
        block_type = block.get("block_type")
        content = parse_json_maybe(block.get("content"))
        if block_type == 10000:
            if isinstance(content, dict):
                for key in ("text", "summary"):
                    value = content.get(key)
                    if isinstance(value, str) and value.strip():
                        parts.append(value.strip())
                thinking = content.get("thinking_block")
                if isinstance(thinking, dict):
                    for key in ("text", "summary", "finish_title"):
                        value = thinking.get(key)
                        if isinstance(value, str) and value.strip():
                            parts.append(value.strip())
            elif isinstance(content, str) and content.strip():
                parts.append(content.strip())
        elif block_type == 10040:
            if isinstance(content, dict):
                title = content.get("finish_title") or content.get("title")
                if isinstance(title, str) and title.strip():
                    parts.append(f"[\u72b6\u6001] {title.strip()}")
        elif block_type in (10010, 10025, 10030, 10058, 10102):
            if isinstance(content, dict):
                for key in ("title", "text", "summary", "finish_title"):
                    value = content.get(key)
                    if isinstance(value, str) and value.strip():
                        parts.append(value.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part not in seen:
            deduped.append(part)
            seen.add(part)
    return "\n\n".join(deduped).strip()


def strip_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    text = text.replace("|", " ")
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def first_sentences(text: str, max_chars: int = 180, max_sentences: int = 2) -> str:
    cleaned = strip_markdown(text)
    if not cleaned:
        return ""
    if cleaned.startswith("[\u72b6\u6001] "):
        cleaned = cleaned[5:].lstrip()
    for prefix in ("\u5df2\u5b8c\u6210PPT\u751f\u6210", "\u5df2\u5b8c\u6210"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].lstrip(" \uff1a:")

    chunks = re.split(r"(?<=[\u3002\uff01\uff1f!?])", cleaned)
    out = ""
    sentence_count = 0
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if out:
            out += " "
        out += chunk
        if chunk[-1] in "\u3002\uff01\uff1f!?":
            sentence_count += 1
        if sentence_count >= max_sentences or len(out) >= max_chars:
            break
    if not out:
        out = cleaned[:max_chars]
    if len(out) > max_chars:
        out = out[: max_chars - 3].rstrip() + "..."
    return out


def summarize_question(question: str) -> str:
    raw = question.strip()
    cleaned = strip_markdown(raw)
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not cleaned:
        return "(\u7a7a\u5185\u5bb9)"
    if raw.startswith("from __future__ import annotations") or ("import mujoco" in raw and len(lines) > 12):
        return "\u8d34\u51fa `run_floating_base.py` \u5168\u6587\uff0c\u8bf7\u6c42\u6574\u4f53\u89e3\u6790"
    if len(lines) > 3 or len(cleaned) > 140:
        first = ""
        for line in lines:
            if line and not line.startswith("```"):
                first = line
                break
        first = first or cleaned[:80]
        if first.startswith(("def ", "class ", "@")) or "mujoco." in first or "=" in first or first.startswith("if "):
            return f"\u89e3\u91ca\u4ee3\u7801\u7247\u6bb5 `{first[:72]}`"
        return cleaned[:96] + ("..." if len(cleaned) > 96 else "")
    return cleaned


def summarize_answer(answer: str) -> str:
    if not answer.strip():
        return "\u65e0\u53ef\u89c1\u56de\u590d\u6587\u672c\u3002"
    return first_sentences(answer, max_chars=180, max_sentences=2)


def theme_for_index(index: int) -> str:
    if 1 <= index <= 141:
        return "A. run_floating_base.py \u4e3b\u5faa\u73af\u4e0e\u53ef\u89c6\u5316"
    if index == 146:
        return "B. \u9996\u6b21 PPT \u6c47\u603b\u8bf7\u6c42"
    if 153 <= index <= 223:
        return "C. sim_robot.py \u63a5\u53e3\u3001\u4f20\u611f\u5668\u4e0e MuJoCo \u6570\u636e"
    if 228 <= index <= 418:
        return "D. TaskScheduler / TaskCommandSource \u4e0e Python \u57fa\u7840"
    if 423 <= index <= 438:
        return "E. \u591a\u6b21\u8c03\u6574 PPT \u8f93\u51fa\u8981\u6c42"
    return "F. \u5bfc\u51fa\u804a\u5929\u6570\u636e"


def build_pairs(payload: dict) -> list[dict]:
    messages = payload["data"]["message_snapshot"]["message_list"]
    assistant_by_reply = {m["reply_id"]: m for m in messages if m.get("user_type") == 2}

    pairs: list[dict] = []
    for message in messages:
        if message.get("user_type") != 1:
            continue
        question_full = extract_text(message)
        answer_message = assistant_by_reply.get(message["message_id"])
        answer_full = extract_text(answer_message) if answer_message else ""
        pairs.append(
            {
                "source_index": message["index"],
                "message_id": message["message_id"],
                "theme": theme_for_index(message["index"]),
                "question_summary": summarize_question(question_full),
                "answer_summary": summarize_answer(answer_full),
                "question_full": strip_markdown(question_full),
                "answer_full": strip_markdown(answer_full),
            }
        )
    return pairs


def build_summary(payload: dict, pairs: list[dict]) -> dict:
    share_info = payload["data"]["share_info"]
    theme_counts: dict[str, int] = {}
    for pair in pairs:
        theme_counts[pair["theme"]] = theme_counts.get(pair["theme"], 0) + 1

    share_time_value = share_info.get("share_time")
    share_time_text = ""
    if isinstance(share_time_value, (int, float)):
        share_time_text = datetime.fromtimestamp(share_time_value / 1000).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "title": share_info.get("share_name") or "\u8c46\u5305\u4f1a\u8bdd\u6458\u8981",
        "share_id": share_info.get("share_id"),
        "share_url": f"https://www.doubao.com/thread/{share_info.get('share_id')}",
        "share_time": share_time_text,
        "total_pairs": len(pairs),
        "theme_counts": theme_counts,
        "pairs": pairs,
    }


def render_html(summary: dict) -> str:
    key_points = [
        "\u4f1a\u8bdd\u4e3b\u7ebf\u662f\u56f4\u7ed5 Stanford Quadruped \u7684 MuJoCo \u4eff\u771f\u4ee3\u7801\u505a\u9010\u6bb5\u5b66\u4e60\uff0c\u5148\u4ece `run_floating_base.py` \u7684\u6574\u4f53\u5165\u53e3\u3001\u4e3b\u5faa\u73af\u3001\u53cd\u9988\u4e0e\u7ed8\u56fe\u5f00\u59cb\uff0c\u518d\u8f6c\u5230\u4eff\u771f\u6865\u63a5\u5c42\u548c\u4efb\u52a1\u8c03\u5ea6\u5c42\u3002",
        "\u7528\u6237\u53cd\u590d\u8ffd\u95ee `MjModel` / `MjData` \u7684\u5173\u7cfb\uff0c\u72b6\u6001\u53d8\u91cf\u5982\u4f55\u4ece MJCF \u6620\u5c04\u5230\u8fd0\u884c\u65f6\u6570\u7ec4\uff0c\u4ee5\u53ca\u4e3a\u4ec0\u4e48 MuJoCo \u7ecf\u5e38\u9700\u8981\u901a\u8fc7 `adr` \u5730\u5740\u7d22\u5f15\u6570\u7ec4\u3002",
        "\u5728 `sim_robot.py` \u76f8\u5173\u9636\u6bb5\uff0c\u5bf9\u8bdd\u91cd\u70b9\u8f6c\u5411\u4f20\u611f\u5668\u3001\u865a\u62df IMU\u3001\u8db3\u7aef\u5750\u6807\u53d8\u6362\u3001\u5173\u8282\u89d2\u8bfb\u53d6\u3001\u72b6\u6001\u540c\u6b65\uff0c\u4ee5\u53ca\u4eff\u771f\u4e0e\u5b9e\u673a\u5728\u8db3\u7aef\u4f4d\u7f6e\u83b7\u53d6\u65b9\u5f0f\u4e0a\u7684\u5dee\u5f02\u3002",
        "\u5728 `TaskCommandSource` / `TaskScheduler` \u9636\u6bb5\uff0c\u7528\u6237\u4e3b\u8981\u60f3\u5f04\u6e05\u695a\u4efb\u52a1\u5e8f\u5217\u3001\u53c2\u6570\u5e73\u6ed1\u6df7\u5408\u3001`transition_time`\u3001\u6b65\u6001\u5207\u6362\u7a33\u5b9a\u6027\uff0c\u4ee5\u53ca `trot -> rest / hop / walk` \u7684\u5de5\u7a0b\u8bed\u4e49\u3002",
        "\u4f1a\u8bdd\u540e\u6bb5\u51fa\u73b0\u591a\u6b21\u5143\u8bf7\u6c42\uff1a\u5e0c\u671b\u628a\u5168\u90e8\u95ee\u7b54\u751f\u6210 PPT\u3001\u7ea0\u6b63 PPT \u6df1\u5ea6\u548c\u8986\u76d6\u8303\u56f4\uff0c\u6700\u540e\u53c8\u5355\u72ec\u8be2\u95ee\u5982\u4f55\u5bfc\u51fa\u8c46\u5305\u804a\u5929\u6570\u636e\u3002",
    ]
    theme_intro = {
        "A. run_floating_base.py \u4e3b\u5faa\u73af\u4e0e\u53ef\u89c6\u5316": "\u8fd9\u4e00\u6bb5\u4ece\u7a0b\u5e8f\u5165\u53e3\u4e00\u8def\u62c6\u5230\u4e3b\u5faa\u73af\u3001\u53cd\u9988\u3001\u53ef\u89c6\u5316\u548c\u4eff\u771f\u7ed3\u675f\u7edf\u8ba1\uff0c\u76ee\u6807\u662f\u5efa\u7acb\u5bf9\u201c\u8bfb\u53d6\u72b6\u6001 \u2192 \u8ba1\u7b97\u63a7\u5236 \u2192 \u6267\u884c\u4eff\u771f \u2192 \u8bb0\u5f55\u7ed3\u679c\u201d\u5168\u6d41\u7a0b\u7684\u76f4\u89c9\u3002",
        "B. \u9996\u6b21 PPT \u6c47\u603b\u8bf7\u6c42": "\u7528\u6237\u7b2c\u4e00\u6b21\u8981\u6c42\u628a\u524d\u9762\u56f4\u7ed5\u4eff\u771f\u6838\u5fc3\u6d41\u7a0b\u7684\u8bb2\u89e3\u6574\u7406\u6210\u4e00\u4efd\u8be6\u7ec6 PPT\uff0c\u8c46\u5305\u5c06\u5176\u8f6c\u6210\u5185\u5bb9\u89c4\u5212\u4efb\u52a1\u3002",
        "C. sim_robot.py \u63a5\u53e3\u3001\u4f20\u611f\u5668\u4e0e MuJoCo \u6570\u636e": "\u8fd9\u4e00\u6bb5\u628a\u5173\u6ce8\u70b9\u4ece\u63a7\u5236\u4e3b\u5faa\u73af\u8f6c\u5230\u4eff\u771f\u6865\u63a5\u5c42\uff0c\u91cd\u70b9\u662f\u89c2\u5bdf\u63a5\u53e3\u3001\u786c\u4ef6\u63a5\u53e3\u3001IMU\u3001\u65f6\u949f\u3001`data` \u6570\u7ec4\u7ed3\u6784\uff0c\u4ee5\u53ca\u4eff\u771f\u4e0e\u5b9e\u673a\u611f\u77e5\u94fe\u6761\u7684\u5dee\u5f02\u3002",
        "D. TaskScheduler / TaskCommandSource \u4e0e Python \u57fa\u7840": "\u8fd9\u662f\u5bf9\u8bdd\u6700\u957f\u7684\u4e00\u6bb5\uff0c\u65e2\u8ba8\u8bba\u8c03\u5ea6\u5668\u672c\u8eab\uff0c\u4e5f\u7a7f\u63d2\u89e3\u91ca `@staticmethod`\u3001`@classmethod`\u3001`self`\u3001`cls`\u3001`set`\u3001`dict` \u7b49 Python \u8bed\u6cd5\u4e0e\u9762\u5411\u5bf9\u8c61\u5199\u6cd5\u3002",
        "E. \u591a\u6b21\u8c03\u6574 PPT \u8f93\u51fa\u8981\u6c42": "\u7528\u6237\u591a\u6b21\u4fee\u6b63\u8f93\u51fa\u9884\u671f\uff0c\u4ece\u201c\u603b\u7ed3\u6210 PPT\u201d\u6539\u6210\u201c\u53ea\u7f57\u5217\u95ee\u7b54\u201d\uff0c\u518d\u8981\u6c42\u8986\u76d6\u4ece\u7b2c\u4e00\u6761\u5230\u6700\u540e\u4e00\u6761\u7684\u5168\u90e8\u5bf9\u8bdd\u3002",
        "F. \u5bfc\u51fa\u804a\u5929\u6570\u636e": "\u6700\u540e\u7528\u6237\u8f6c\u5411\u64cd\u4f5c\u6027\u95ee\u9898\uff0c\u8be2\u95ee\u5982\u4f55\u5bfc\u51fa\u8c46\u5305\u804a\u5929\u6570\u636e\u3002",
    }
    ordered_themes = [
        "A. run_floating_base.py \u4e3b\u5faa\u73af\u4e0e\u53ef\u89c6\u5316",
        "B. \u9996\u6b21 PPT \u6c47\u603b\u8bf7\u6c42",
        "C. sim_robot.py \u63a5\u53e3\u3001\u4f20\u611f\u5668\u4e0e MuJoCo \u6570\u636e",
        "D. TaskScheduler / TaskCommandSource \u4e0e Python \u57fa\u7840",
        "E. \u591a\u6b21\u8c03\u6574 PPT \u8f93\u51fa\u8981\u6c42",
        "F. \u5bfc\u51fa\u804a\u5929\u6570\u636e",
    ]
    css = """
@page { size: A4; margin: 14mm 12mm 14mm 12mm; }
@font-face {
  font-family: "SummaryCJK";
  src: local("Microsoft YaHei"), local("\\5FAE\\8F6F\\96C5\\9ED1"), local("SimSun"), local("\\5B8B\\4F53"), local("SimHei"), local("\\9ED1\\4F53");
}
body {
  font-family: "SummaryCJK", "Microsoft YaHei", "SimSun", "Noto Sans CJK SC", sans-serif;
  color: #1f2937;
  background: #f5f7fb;
  margin: 0;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
main { width: 100%; }
.section { background: white; border: 1px solid #dde3ee; border-radius: 12px; padding: 18px 20px; margin: 0 0 14px 0; box-shadow: 0 1px 0 rgba(0,0,0,0.03); }
.cover { padding: 26px 28px; background: linear-gradient(135deg, #0f172a, #1d4ed8 55%, #60a5fa); color: white; border: none; }
.h1 { font-size: 26px; font-weight: 700; margin: 0 0 8px 0; }
.h2 { font-size: 18px; font-weight: 700; margin: 0 0 10px 0; color: #0f172a; }
.meta { font-size: 12px; opacity: 0.92; line-height: 1.6; }
.kpis { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
.kpi { background: rgba(255,255,255,0.13); border: 1px solid rgba(255,255,255,0.22); border-radius: 10px; padding: 10px 12px; min-width: 110px; }
.kpi strong { display: block; font-size: 18px; }
ul.flat { margin: 0; padding-left: 18px; }
ul.flat li { margin: 0 0 8px 0; line-height: 1.55; }
.theme-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.theme-card { border: 1px solid #d7deeb; border-radius: 10px; padding: 12px; background: #f8fafc; }
.theme-card .name { font-weight: 700; margin-bottom: 4px; color: #0f172a; }
.theme-card .count { color: #1d4ed8; font-weight: 700; margin-top: 6px; }
.pair { border-top: 1px solid #e5e7eb; padding-top: 12px; margin-top: 12px; }
.pair:first-child { border-top: none; padding-top: 0; margin-top: 0; }
.pair-head { font-size: 12px; color: #475569; margin-bottom: 6px; }
.label { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #dbeafe; color: #1e3a8a; font-size: 11px; margin-left: 8px; }
.qa { margin: 0 0 6px 0; line-height: 1.55; }
.qa strong { color: #0f172a; }
.footer-note { font-size: 11px; color: #64748b; line-height: 1.5; }
.page-break { break-before: page; }
a { color: inherit; }
.small { font-size: 12px; color: #475569; }
"""

    parts: list[str] = []
    parts.append('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">')
    parts.append(f"<title>{html.escape('\u8c46\u5305\u4f1a\u8bdd\u95ee\u7b54\u603b\u7ed3')}</title>")
    parts.append(f"<style>{css}</style></head><body><main>")

    parts.append('<section class="section cover">')
    parts.append(f'<div class="h1">{html.escape("\u8c46\u5305\u4f1a\u8bdd\u95ee\u7b54\u603b\u7ed3")}</div>')
    parts.append(f'<div style="font-size:15px;margin-bottom:12px;">{html.escape(summary["title"])}</div>')
    parts.append(
        '<div class="meta">'
        f'{html.escape("\u6765\u6e90")}：<a href="{html.escape(summary["share_url"])}">{html.escape(summary["share_url"])}</a><br>'
        f'{html.escape("\u5206\u4eab\u65f6\u95f4")}：{html.escape(summary["share_time"] or "\u672a\u63d0\u4f9b")}<br>'
        f'{html.escape("\u751f\u6210\u65f6\u95f4")}：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        "</div>"
    )
    parts.append('<div class="kpis">')
    parts.append(f'<div class="kpi"><strong>{summary["total_pairs"]}</strong>{"\u7ec4\u95ee\u7b54"}</div>')
    parts.append(
        f'<div class="kpi"><strong>{summary["theme_counts"].get(ordered_themes[0], 0)}</strong>{"\u7ec4\u4e3b\u5faa\u73af\u76f8\u5173"}</div>'
    )
    parts.append(
        f'<div class="kpi"><strong>{summary["theme_counts"].get(ordered_themes[2], 0)}</strong>{"\u7ec4\u6865\u63a5\u5c42\u76f8\u5173"}</div>'
    )
    parts.append(
        f'<div class="kpi"><strong>{summary["theme_counts"].get(ordered_themes[3], 0)}</strong>{"\u7ec4\u8c03\u5ea6\u5668/Python \u76f8\u5173"}</div>'
    )
    parts.append("</div></section>")

    parts.append(f'<section class="section"><div class="h2">{html.escape("\u4f1a\u8bdd\u603b\u89c8")}</div><ul class="flat">')
    for item in key_points:
        parts.append(f"<li>{html.escape(item)}</li>")
    parts.append("</ul></section>")

    parts.append(f'<section class="section"><div class="h2">{html.escape("\u4e3b\u9898\u5206\u5e03")}</div><div class="theme-grid">')
    for theme in ordered_themes:
        count = summary["theme_counts"].get(theme, 0)
        if not count:
            continue
        parts.append('<div class="theme-card">')
        parts.append(f'<div class="name">{html.escape(theme)}</div>')
        parts.append(f'<div class="small">{html.escape(theme_intro[theme])}</div>')
        parts.append(f'<div class="count">{count} {"\u7ec4\u95ee\u7b54"}</div>')
        parts.append("</div>")
    parts.append("</div></section>")

    for i, theme in enumerate(ordered_themes):
        theme_pairs = [pair for pair in summary["pairs"] if pair["theme"] == theme]
        if not theme_pairs:
            continue
        cls = "section page-break" if i > 0 else "section"
        parts.append(f'<section class="{cls}">')
        parts.append(f'<div class="h2">{html.escape(theme)}</div>')
        parts.append(f'<div class="small" style="margin-bottom:10px;">{html.escape(theme_intro[theme])}</div>')
        for pair in theme_pairs:
            parts.append('<div class="pair">')
            parts.append(
                f'<div class="pair-head">{"\u6e90\u7d22\u5f15"} {pair["source_index"]}'
                f'<span class="label">{html.escape(theme)}</span></div>'
            )
            parts.append(f'<p class="qa"><strong>{"\u95ee\u9898"}：</strong>{html.escape(pair["question_summary"])}</p>')
            parts.append(f'<p class="qa"><strong>{"\u56de\u7b54\u8981\u70b9"}：</strong>{html.escape(pair["answer_summary"])}</p>')
            parts.append("</div>")
        parts.append("</section>")

    parts.append(f'<section class="section"><div class="h2">{html.escape("\u8bf4\u660e")}</div>')
    parts.append(
        '<div class="footer-note">'
        "1. \u672c\u6587\u6863\u57fa\u4e8e\u516c\u5f00\u5206\u4eab\u9875\u4e2d\u53ef\u89c1\u7684\u6d88\u606f\u5feb\u7167\u81ea\u52a8\u62bd\u53d6\u3002<br>"
        "2. \u4e3a\u4fbf\u4e8e\u9605\u8bfb\uff0c\u8be6\u7ec6\u56de\u7b54\u5df2\u538b\u7f29\u4e3a\u201c\u56de\u7b54\u8981\u70b9\u201d\uff0c\u672a\u9010\u5b57\u8f6c\u5f55\u3002<br>"
        "3. \u7eaf\u72b6\u6001\u578b\u56de\u590d\uff08\u5982\u201c\u5df2\u5b8c\u6210PPT\u751f\u6210\u201d\uff09\u82e5\u540c\u65f6\u5305\u542b\u4efb\u52a1\u8bf4\u660e\uff0c\u4f1a\u4fdd\u7559\u5176\u8bf4\u660e\u6458\u8981\uff1b\u5426\u5219\u53ea\u4fdd\u7559\u72b6\u6001\u542b\u4e49\u3002"
        "</div>"
    )
    parts.append("</section>")
    parts.append("</main></body></html>")
    return "".join(parts)


def export_pdf(html_path: Path, pdf_path: Path, browser_path: Path) -> None:
    cmd = [
        str(browser_path),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main() -> None:
    args = parse_args()
    workdir = args.workdir.resolve()

    raw_html_path = workdir / RAW_HTML_NAME
    if not raw_html_path.exists():
        raise FileNotFoundError(f"Raw Doubao HTML not found: {raw_html_path}")

    payload = load_message_payload(raw_html_path)
    pairs = build_pairs(payload)
    summary = build_summary(payload, pairs)
    html_text = render_html(summary)

    (workdir / PAIRS_JSON_NAME).write_text(
        json.dumps(pairs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (workdir / SUMMARY_JSON_NAME).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (workdir / SUMMARY_HTML_NAME).write_text(html_text, encoding="utf-8")

    if args.skip_pdf:
        return

    edge_path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    if edge_path.exists():
        export_pdf(workdir / SUMMARY_HTML_NAME, workdir / SUMMARY_PDF_NAME, edge_path)
    if chrome_path.exists():
        export_pdf(workdir / SUMMARY_HTML_NAME, workdir / SUMMARY_CHROME_PDF_NAME, chrome_path)


if __name__ == "__main__":
    main()
