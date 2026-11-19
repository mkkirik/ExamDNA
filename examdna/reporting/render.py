"""Exam rendering: student paper (Markdown + print-ready HTML), answer key, marking guide.

The student paper never contains answers, lineage or validation details.
"""

from __future__ import annotations

import html
from typing import Any, Dict, List

from .i18n import labels


def _marks_label(n: int, L: dict) -> str:
    return f"[{n} {L['mark'] if n == 1 else L['marks']}]"


def _md_table(table: Dict[str, Any]) -> List[str]:
    cols = table.get("columns") or []
    rows = table.get("rows") or []
    if not cols:
        return []
    out = []
    if table.get("caption"):
        out.append(f"*{table['caption']}*")
        out.append("")
    out.append("| " + " | ".join(cols) + " |")
    out.append("|" + "|".join(" --- " for _ in cols) + "|")
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    out.append("")
    return out


def exam_markdown(exam: Dict[str, Any]) -> str:
    L = labels(exam.get("language", "en"))
    lines = [f"# {exam['title']}", ""]
    meta = []
    if exam.get("subject"):
        meta.append(f"**{exam['subject']}**")
    meta.append(f"**{L['total_marks']}:** {exam['total_marks']}")
    if exam.get("time_minutes"):
        meta.append(f"**{L['time']}:** {exam['time_minutes']} {L['minutes']}")
    lines += [" · ".join(meta), "", f"{L['name']}: ______________________   {L['date']}: ____________", ""]
    lines += [f"## {L['instructions']}", ""] + [f"- {i}" for i in exam.get("instructions") or []] + [""]
    for sec in exam["sections"]:
        title = f"## {L['section']} {sec['label']}" + (f" — {sec['title']}" if sec.get("title") else "") + f" ({sec['marks']} {L['marks']})"
        lines += ["---", "", title, ""]
        if sec.get("instructions"):
            lines += [f"*{sec['instructions']}*", ""]
        for item in sec["questions"]:
            q = item["question"]
            head = f"**{item['number']}.** {q['text']}"
            if not q.get("parts"):
                head += f" {_marks_label(q['marks'], L)}"
            lines += [head, ""]
            if q.get("table"):
                lines += _md_table(q["table"])
            if q.get("diagram_description"):
                lines += [f"> {q['diagram_description']}", ""]
            for opt in q.get("options") or []:
                lines.append(f"- **{opt['key']}.** {opt['text']}")
            if q.get("options"):
                lines.append("")
            for part in q.get("parts") or []:
                pm = f" {_marks_label(part['marks'], L)}" if part.get("marks") is not None else ""
                lines += [f"&nbsp;&nbsp;**({part['label']})** {part['text']}{pm}", ""]
            lines.append("")
    lines += ["---", "", f"*{L['unofficial']}*", ""]
    return "\n".join(lines)


CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
:root { --ink: #1d1d1f; --muted: #5f6368; --rule: #c8c8cc; --accent: #c8102e; }
* { box-sizing: border-box; }
body { font-family: "Georgia", "Times New Roman", serif; color: var(--ink); line-height: 1.45; max-width: 178mm; margin: 0 auto; padding: 12px 16px; font-size: 11.5pt; background: #fff; }
header.paper { border-bottom: 2px solid var(--ink); padding-bottom: 8px; margin-bottom: 14px; }
header.paper h1 { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 20pt; margin: 0 0 4px; }
.meta { display: flex; flex-wrap: wrap; gap: 6px 22px; font-family: "Helvetica Neue", Arial, sans-serif; font-size: 10pt; color: var(--muted); }
.candidate { display: flex; gap: 24px; margin: 12px 0 4px; font-size: 10.5pt; }
.candidate span { flex: 1; border-bottom: 1px solid var(--ink); padding-bottom: 2px; }
.instructions { border: 1px solid var(--rule); padding: 8px 14px; margin: 12px 0 18px; font-size: 10.5pt; }
.instructions h2 { font-size: 11pt; margin: 0 0 4px; font-family: "Helvetica Neue", Arial, sans-serif; }
.instructions ul { margin: 0; padding-left: 18px; }
section.exam-section { margin-top: 18px; }
section.exam-section > h2 { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 13pt; border-bottom: 1px solid var(--ink); padding-bottom: 3px; display: flex; justify-content: space-between; }
.section-note { font-style: italic; color: var(--muted); font-size: 10pt; }
.q { margin: 14px 0 6px; page-break-inside: avoid; break-inside: avoid; }
.q-head { display: flex; gap: 10px; align-items: baseline; }
.q-num { font-weight: bold; font-family: "Helvetica Neue", Arial, sans-serif; min-width: 1.8em; }
.q-text { flex: 1; }
.q-marks { white-space: nowrap; font-family: "Helvetica Neue", Arial, sans-serif; font-size: 10pt; }
.part { display: flex; gap: 10px; margin: 8px 0 0 2.4em; align-items: baseline; }
.part-label { min-width: 2em; }
.answer-lines { margin: 6px 0 0 2.4em; }
.answer-lines div { border-bottom: 1px dotted #9a9a9f; height: 8.5mm; }
table.data { border-collapse: collapse; margin: 8px 0 4px 2.4em; font-size: 10.5pt; }
table.data th, table.data td { border: 1px solid var(--ink); padding: 3px 10px; text-align: center; }
table.data caption { caption-side: top; text-align: left; font-style: italic; padding-bottom: 3px; }
.figure { margin: 8px 0 0 2.4em; padding: 6px 10px; border-left: 3px solid var(--rule); font-size: 10.5pt; color: #333; }
ol.options { list-style: none; margin: 6px 0 0 2.4em; padding: 0; }
ol.options li { margin: 2px 0; }
footer.paper { margin-top: 26px; border-top: 1px solid var(--rule); padding-top: 6px; font-size: 8.5pt; color: var(--muted); text-align: center; }
@media print { body { padding: 0; } .no-print { display: none; } section.exam-section { page-break-before: auto; } }
@media (max-width: 480px) { body { font-size: 11pt; padding: 8px 16px; } .part, .answer-lines, table.data, ol.options, .figure { margin-left: 1.2em; } .candidate { flex-direction: column; gap: 10px; } }
"""


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s)).replace("\n", "<br>")


def _lines_for(marks: int, explicit: Any = None) -> int:
    if isinstance(explicit, int):
        return explicit
    return min(2 + marks * 2, 14)


def exam_html(exam: Dict[str, Any], answer_space: bool = True) -> str:
    L = labels(exam.get("language", "en"))
    out = [
        "<!doctype html>",
        f'<html lang="{_esc(exam.get("language", "en"))}"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_esc(exam['title'])}</title><style>{CSS}</style></head><body>",
        '<header class="paper">',
        f"<h1>{_esc(exam['title'])}</h1>",
        '<div class="meta">',
    ]
    if exam.get("subject"):
        out.append(f"<span>{_esc(exam['subject'])}</span>")
    out.append(f"<span>{_esc(L['total_marks'])}: <strong>{exam['total_marks']}</strong></span>")
    if exam.get("time_minutes"):
        out.append(f"<span>{_esc(L['time'])}: {exam['time_minutes']} {_esc(L['minutes'])}</span>")
    out += ["</div>", f'<div class="candidate"><span>{_esc(L["name"])}:</span><span>{_esc(L["date"])}:</span></div>', "</header>"]
    out += ['<div class="instructions">', f"<h2>{_esc(L['instructions'])}</h2><ul>"]
    out += [f"<li>{_esc(i)}</li>" for i in exam.get("instructions") or []]
    out += ["</ul></div>"]
    for sec in exam["sections"]:
        title = f"{_esc(L['section'])} {_esc(sec['label'])}" + (f" — {_esc(sec['title'])}" if sec.get("title") else "")
        out.append(f'<section class="exam-section"><h2><span>{title}</span><span>{sec["marks"]} {_esc(L["marks"])}</span></h2>')
        if sec.get("instructions"):
            out.append(f'<p class="section-note">{_esc(sec["instructions"])}</p>')
        for item in sec["questions"]:
            q = item["question"]
            out.append('<div class="q">')
            marks_html = "" if q.get("parts") else f'<span class="q-marks">{_esc(_marks_label(q["marks"], L))}</span>'
            out.append(f'<div class="q-head"><span class="q-num">{item["number"]}.</span><span class="q-text">{_esc(q["text"])}</span>{marks_html}</div>')
            t = q.get("table")
            if t and t.get("columns"):
                out.append('<table class="data">')
                if t.get("caption"):
                    out.append(f"<caption>{_esc(t['caption'])}</caption>")
                out.append("<tr>" + "".join(f"<th>{_esc(c)}</th>" for c in t["columns"]) + "</tr>")
                for r in t.get("rows") or []:
                    out.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>")
                out.append("</table>")
            if q.get("diagram_description"):
                out.append(f'<div class="figure">{_esc(q["diagram_description"])}</div>')
            if q.get("options"):
                out.append('<ol class="options">' + "".join(f"<li><strong>{_esc(o['key'])}.</strong> {_esc(o['text'])}</li>" for o in q["options"]) + "</ol>")
            if q.get("parts"):
                for part in q["parts"]:
                    pm = f'<span class="q-marks">{_esc(_marks_label(part["marks"], L))}</span>' if part.get("marks") is not None else ""
                    out.append(f'<div class="part"><span class="part-label">({_esc(part["label"])})</span><span class="q-text">{_esc(part["text"])}</span>{pm}</div>')
                    if answer_space:
                        n = _lines_for(part.get("marks") or 1, part.get("answer_space_lines"))
                        out.append('<div class="answer-lines">' + "<div></div>" * n + "</div>")
            elif answer_space and q.get("question_type") != "multiple_choice":
                out.append('<div class="answer-lines">' + "<div></div>" * _lines_for(q["marks"]) + "</div>")
            out.append("</div>")
        out.append("</section>")
    out += [f'<footer class="paper">{_esc(L["unofficial"])}</footer>', "</body></html>"]
    return "\n".join(out)


def answer_key_markdown(exam: Dict[str, Any]) -> str:
    L = labels(exam.get("language", "en"))
    lines = [f"# {exam['title']} — {L['answer_key']}", "", f"*{L['confidential']}*", ""]
    for sec in exam["sections"]:
        lines += [f"## {L['section']} {sec['label']}", ""]
        for item in sec["questions"]:
            q = item["question"]
            m = q.get("marking") or {}
            flag = f" — **{L['review_flag']}**" if item["validation_state"] != "PASS" else ""
            lines.append(f"**{item['number']}.** {_marks_label(q['marks'], L)}{flag}")
            if m.get("answer_key"):
                lines.append(f"- {L['final_answer']}: **{m['answer_key']}**" + (f" ({m['final_answer']})" if m.get("final_answer") else ""))
            elif m.get("final_answer"):
                lines.append(f"- {L['final_answer']}: **{m['final_answer']}**")
            else:
                lines.append(f"- {L['no_answer']}")
            if m.get("accept_rule"):
                lines.append(f"- {L['accept_rule']}: {m['accept_rule']}")
            if m.get("worked_solution"):
                lines += ["", f"  *{L['worked_solution']}:* {m['worked_solution']}"]
            lines.append("")
    return "\n".join(lines)


def marking_guide_markdown(exam: Dict[str, Any]) -> str:
    L = labels(exam.get("language", "en"))
    lines = [f"# {exam['title']} — {L['marking_guide']}", "", f"*{L['confidential']}*", ""]
    lines += [f"{L['total_marks']}: **{exam['total_marks']}**", ""]
    for sec in exam["sections"]:
        lines += [f"## {L['section']} {sec['label']} ({sec['marks']} {L['marks']})", ""]
        for item in sec["questions"]:
            q = item["question"]
            m = q.get("marking") or {}
            lin = item.get("lineage") or {}
            origin = f"{lin.get('operator')} ← {lin.get('parent_id')}" if lin else "source"
            lines.append(f"### {L['question']} {item['number']} — {q['marks']} {L['marks']}  ")
            lines.append(f"`{q['id']}` · {L['lineage']}: {origin} · validation: **{item['validation_state']}**")
            lines.append("")
            pts = m.get("points") or []
            if pts:
                lines.append("| # | " + L["marking_points"] + " | " + L["marks"] + " |")
                lines.append("| --- | --- | --- |")
                for i, p in enumerate(pts, 1):
                    part = f"({p['part']}) " if p.get("part") else ""
                    lines.append(f"| {i} | {part}{p['description']} | {p['marks']} |")
                lines.append("")
            else:
                lines += [f"- {L['no_answer']}", ""]
    return "\n".join(lines)
