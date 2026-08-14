"""导出（PRD 5.7）：Markdown（模板）+ PDF（A4 纸感打印排版 HTML）。"""
import json
from datetime import date

from sqlalchemy.orm import Session

from app.db.models import KnowledgePoint, Mistake
from app.services.mistake_service import list_mistakes, serialize_detail

PAPER_BG = "#F7F4EE"
INK = "#2B2B28"
RED_INK = "#D64545"


def _collect(db: Session, filters: dict, limit: int = 200) -> list[dict]:
    result = list_mistakes(db, **filters, page=1, page_size=limit)
    items = []
    for item in result["items"]:
        items.append(serialize_detail(db, db.get(Mistake, item["id"])))
    return items


def _excerpt_options(options: list[str]) -> str:
    return "\n".join(f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options))


def build_markdown(db: Session, filters: dict) -> tuple[str, int]:
    """Markdown 模板：题号/题干/选项/答案/解析/错因/知识点/复习次数/掌握状态。"""
    items = _collect(db, filters)
    total = list_mistakes(db, **filters, page=1, page_size=1)["total"]
    lines = [f"# Recall 错题导出", "",
             f"- 导出日期：{date.today().isoformat()}",
             f"- 本文件题数：{len(items)}（筛选结果共 {total} 题）", ""]
    status_labels = {"pending": "未开始", "wrong": "未掌握", "fixing": "待巩固", "mastered": "已掌握"}
    error_labels = {"knowledge": "知识性错误", "logic": "逻辑错误", "reading": "审题错误",
                    "calculation": "计算错误", "concept": "概念混淆", "careless": "粗心", "other": "其他"}
    for i, item in enumerate(items, 1):
        lines.append(f"## {i}. {item['question_text']}")
        if item["options"]:
            lines.append("")
            lines.append(_excerpt_options(item["options"]))
        lines.append("")
        lines.append(f"**答案**：{item['answer_text'] or '—'}")
        lines.append("")
        lines.append(f"**解析**：{item['analysis'] or '—'}")
        lines.append("")
        lines.append(f"- 错因：{error_labels.get(item['error_type'], item['error_type'])}")
        lines.append(f"- 知识点：{item['knowledge_point'] or '—'}（{item['subject_name']}）")
        lines.append(f"- 复习次数：{item['review_count']} · 掌握状态：{status_labels.get(item['status'], item['status'])} · 掌握度 {round(item['mastery'] * 100)}%")
        lines.append("")
    return "\n".join(lines), total


def build_pdf_html(db: Session, filters: dict) -> tuple[str, int]:
    """PDF 打印排版（方案 B 纸感样式）：封面统计摘要 + 逐题详情，A4。"""
    items = _collect(db, filters)
    total = list_mistakes(db, **filters, page=1, page_size=1)["total"]
    status_labels = {"pending": "未开始", "wrong": "未掌握", "fixing": "待巩固", "mastered": "已掌握"}
    status_colors = {"pending": "#6B7280", "wrong": "#DC2626", "fixing": "#EA8C00", "mastered": "#16A34A"}
    mastered = sum(1 for it in items if it["status"] == "mastered")
    card_html = []
    for i, item in enumerate(items, 1):
        options_html = "".join(
            f"<div class='opt'>{chr(65 + k)}. {opt}</div>"
            for k, opt in enumerate(item["options"])
        )
        card_html.append(f"""
        <section class="qcard">
          <div class="qhead"><span class="qnum">{i}</span>
            <span class="chip" style="color:{status_colors.get(item['status'], '#6B7280')}; border:1px solid {status_colors.get(item['status'], '#6B7280')};">{status_labels.get(item['status'], item['status'])}</span>
            <span class="qmeta">{item['subject_name']} · {item['knowledge_point'] or '未分类'}</span>
          </div>
          <div class="qtext">{item['question_text']}</div>
          {options_html}
          <div class="answer">答案：{item['answer_text'] or '—'}</div>
          <div class="analysis">{item['analysis'] or '暂无解析'}</div>
          <div class="foot">错因：{item['error_type']} · 复习 {item['review_count']} 次 · 掌握度 {round(item['mastery'] * 100)}%</div>
        </section>""")
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>Recall 错题导出 - {date.today().isoformat()}</title>
<style>
  @page {{ size: A4; margin: 18mm 16mm; }}
  body {{ font-family: "PingFang SC","Microsoft YaHei",sans-serif; background:{PAPER_BG}; color:{INK}; margin:0; padding:24px; }}
  .cover {{ text-align:center; padding:48px 0 24px; border-bottom:2px solid {INK}; margin-bottom:24px; }}
  .cover h1 {{ font-size:24px; margin:0 0 8px; }}
  .cover .stats {{ font-size:13px; color:#6E6A61; }}
  .stats b {{ color:{INK}; font-size:18px; margin:0 4px; }}
  .qcard {{ background:#FFFFFF; border:1px solid #E3DED3; border-radius:6px; padding:16px 18px; margin-bottom:16px; page-break-inside:avoid; }}
  .qhead {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
  .qnum {{ background:{INK}; color:#fff; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:12px; }}
  .chip {{ font-size:11px; padding:2px 8px; border-radius:10px; }}
  .qmeta {{ font-size:12px; color:#6E6A61; margin-left:auto; }}
  .qtext {{ font-size:14px; line-height:1.7; margin-bottom:8px; }}
  .opt {{ font-size:13px; margin:2px 0 2px 8px; }}
  .answer {{ font-size:13px; color:{RED_INK}; font-weight:600; margin-top:8px; }}
  .analysis {{ font-size:13px; color:{INK}; margin-top:6px; line-height:1.7; }}
  .foot {{ font-size:11px; color:#6E6A61; margin-top:10px; border-top:1px dashed #E3DED3; padding-top:6px; }}
  @media print {{ body {{ padding:0; background:#fff; }} .qcard {{ border-color:#ddd; }} }}
</style></head>
<body>
  <div class="cover">
    <h1>Recall 错题集</h1>
    <div class="stats">共 <b>{total}</b> 题（本文件 <b>{len(items)}</b> 题） · 已掌握 <b>{mastered}</b> · 导出日期 {date.today().isoformat()}</div>
  </div>
  {''.join(card_html)}
</body></html>"""
    return html, total
