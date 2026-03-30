from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)


def register_fonts() -> None:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def build_styles():
    styles = getSampleStyleSheet()
    base_font = "STSong-Light"

    styles["Normal"].fontName = base_font
    styles["Normal"].fontSize = 11
    styles["Normal"].leading = 17

    styles.add(
        ParagraphStyle(
            name="CNTitle",
            parent=styles["Title"],
            fontName=base_font,
            fontSize=22,
            leading=30,
            spaceAfter=14,
            textColor=colors.HexColor("#111111"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNH1",
            parent=styles["Heading1"],
            fontName=base_font,
            fontSize=18,
            leading=25,
            spaceBefore=10,
            spaceAfter=8,
            textColor=colors.HexColor("#111111"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNH2",
            parent=styles["Heading2"],
            fontName=base_font,
            fontSize=15,
            leading=22,
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor("#222222"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNH3",
            parent=styles["Heading3"],
            fontName=base_font,
            fontSize=13,
            leading=20,
            spaceBefore=6,
            spaceAfter=4,
            textColor=colors.HexColor("#333333"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNBullet",
            parent=styles["Normal"],
            fontName=base_font,
            fontSize=11,
            leading=17,
            leftIndent=14,
            firstLineIndent=-10,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNQuote",
            parent=styles["Normal"],
            fontName=base_font,
            fontSize=10.5,
            leading=16,
            leftIndent=14,
            rightIndent=8,
            textColor=colors.HexColor("#444444"),
            borderPadding=6,
            backColor=colors.HexColor("#F4F4F4"),
            spaceBefore=4,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNCode",
            parent=styles["Code"],
            fontName=base_font,
            fontSize=9.5,
            leading=13,
            leftIndent=10,
            rightIndent=10,
            borderPadding=8,
            backColor=colors.HexColor("#F7F7F7"),
            borderColor=colors.HexColor("#DDDDDD"),
            borderWidth=0.5,
            borderRadius=2,
            spaceBefore=4,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNCaption",
            parent=styles["Normal"],
            fontName=base_font,
            fontSize=10,
            leading=14,
            alignment=1,
            textColor=colors.HexColor("#555555"),
            spaceBefore=4,
            spaceAfter=8,
        )
    )
    return styles


def format_inline_text(text: str) -> str:
    text = html.escape(text)

    code_tokens: list[str] = []

    def replace_code(match: re.Match[str]) -> str:
        code_tokens.append(match.group(1))
        return f"@@CODE{len(code_tokens) - 1}@@"

    text = re.sub(r"`([^`]+)`", replace_code, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)

    for index, token in enumerate(code_tokens):
        escaped_token = html.escape(token)
        text = text.replace(
            f"@@CODE{index}@@",
            f'<font backColor="#F3F4F6">‹{escaped_token}›</font>',
        )
    return text


def page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("STSong-Light", 9)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(canvas.getPageNumber()))
    canvas.restoreState()


def markdown_to_story(markdown_text: str, base_dir: Path):
    styles = build_styles()
    story = []
    paragraph_lines: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        text = " ".join(line.strip() for line in paragraph_lines).strip()
        paragraph_lines = []
        if not text:
            return
        story.append(Paragraph(format_inline_text(text), styles["Normal"]))
        story.append(Spacer(1, 4))

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            if not in_code:
                in_code = True
                code_lines = []
            else:
                story.append(Preformatted("\n".join(code_lines), styles["CNCode"]))
                in_code = False
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            continue

        if stripped == "---":
            flush_paragraph()
            story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#CCCCCC")))
            story.append(Spacer(1, 6))
            continue

        image_match = re.match(r"^!\[(.*?)\]\((.+?)\)$", stripped)
        if image_match:
            flush_paragraph()
            alt_text = image_match.group(1).strip()
            image_path = (base_dir / image_match.group(2).strip()).resolve()
            if image_path.exists():
                with PILImage.open(image_path) as img:
                    width_px, height_px = img.size
                max_width = A4[0] - 36 * mm
                max_height = 120 * mm
                scale = min(max_width / width_px, max_height / height_px)
                figure = RLImage(str(image_path), width=width_px * scale, height=height_px * scale)
                figure.hAlign = "CENTER"
                flowables = [figure]
                if alt_text:
                    flowables.append(Paragraph(format_inline_text(alt_text), styles["CNCaption"]))
                else:
                    flowables.append(Spacer(1, 6))
                story.append(KeepTogether(flowables))
            else:
                story.append(Paragraph(format_inline_text(f"[缺失图片] {image_path}"), styles["CNCaption"]))
            continue

        if line.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(format_inline_text(line[2:].strip()), styles["CNTitle"]))
            story.append(Spacer(1, 6))
            continue

        if line.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(format_inline_text(line[3:].strip()), styles["CNH1"]))
            continue

        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(format_inline_text(line[4:].strip()), styles["CNH2"]))
            continue

        if line.startswith("#### "):
            flush_paragraph()
            story.append(Paragraph(format_inline_text(line[5:].strip()), styles["CNH3"]))
            continue

        if line.startswith("> "):
            flush_paragraph()
            story.append(Paragraph(format_inline_text(line[2:].strip()), styles["CNQuote"]))
            continue

        bullet_match = re.match(r"^(\s*)- (.+)$", line)
        if bullet_match:
            flush_paragraph()
            content = bullet_match.group(2).strip()
            story.append(Paragraph("• " + format_inline_text(content), styles["CNBullet"]))
            continue

        ordered_match = re.match(r"^(\s*)(\d+)\. (.+)$", line)
        if ordered_match:
            flush_paragraph()
            index = ordered_match.group(2)
            content = ordered_match.group(3).strip()
            story.append(Paragraph(f"{index}. " + format_inline_text(content), styles["CNBullet"]))
            continue

        paragraph_lines.append(line)

    flush_paragraph()
    if in_code and code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["CNCode"]))

    return story


def export_markdown_pdf(input_path: Path, output_path: Path) -> None:
    register_fonts()
    markdown_text = input_path.read_text(encoding="utf-8")
    story = markdown_to_story(markdown_text, input_path.parent)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=input_path.stem,
        author="OpenAI Codex",
    )
    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python docs/export_markdown_pdf.py <input.md> <output.pdf>")
        return 1
    input_path = Path(argv[1]).resolve()
    output_path = Path(argv[2]).resolve()
    export_markdown_pdf(input_path, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
