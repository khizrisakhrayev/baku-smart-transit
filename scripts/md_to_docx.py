"""Convert a Markdown document to Word (.docx) with python-docx.

Usage (from the project folder):
    venv/Scripts/python.exe scripts/md_to_docx.py docs/TEXNIKI_IZAH.md docs/TEXNIKI_IZAH.docx

Needs: pip install python-docx. The Markdown file is only read, never changed.

Supported Markdown (enough for this project's docs):
- `# title` (used for the title page), `##` / `###` / `####` headings
- paragraphs, `- ` bullet items and `1. ` numbered items (with indented continuation lines)
- `| tables |`, fenced ``` code blocks, `---` rules (skipped)
- inline **bold** and `code`
Images from docs/screenshots/ are added at the end under "Ekran şəkilləri".
"""
import re
import sys
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Calibri"
CODE_FONT = "Consolas"
PROJECT_NAME = "Bakı Ağıllı Nəqliyyat və Kraudsorsinq Mühərriki"
PROJECT_NAME_EN = "Baku Smart Transit & Crowdsourcing Engine"
SUBTITLE = "Texniki izah"
TEAM = [
    ("Ülvi Mustafayev", "Backend və API"),
    ("Anar Hümmətli", "Frontend və UI/UX"),
    ("Xizri Saxrayev", "Süni intellekt inteqrasiyası, testləşdirmə və sənədləşmə"),
]
MONTHS_AZ = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
             "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"]

SCREENSHOT_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
# Known screenshots in a sensible order, with Azerbaijani captions; any other image follows.
SCREENSHOT_CAPTIONS = {
    "passenger-map": "Sərnişin paneli: seçilmiş marşrutlar və avtobuslar xəritədə",
    "passenger-eta": "Sərnişin paneli: dayanacağa gəliş vaxtları və alternativlər",
    "passenger-report": "Sərnişin paneli: sıxlıq bildirişi",
    "operator-map": "Operator paneli: şəbəkə xəritəsi və marşrut siyahısı",
    "operator-alerts": "Operator paneli: xəbərdarlıqlar və yönləndirmə tövsiyəsi",
    "operator-analytics": "Operator paneli: analitika",
}

INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")
LIST_ITEM = re.compile(r"^(?:- |(\d+)\. )(.*)$")


# --- Small formatting helpers ---

def set_font(style_or_run, name: str, size: float | None = None) -> None:
    """Set a font for Latin and complex scripts (so Azerbaijani letters use it too)."""
    font = style_or_run.font
    font.name = name
    if size:
        font.size = Pt(size)
    r_pr = style_or_run.element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.append(r_fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        r_fonts.set(qn(attr), name)


def shade(element, fill: str) -> None:
    """Background colour for a paragraph or table cell."""
    props = element.get_or_add_pPr() if hasattr(element, "get_or_add_pPr") else element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    props.append(shd)


def add_inline(paragraph, text: str) -> None:
    """Add text with **bold** and `code` runs."""
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            set_font(paragraph.add_run(part[1:-1]), CODE_FONT)
        else:
            paragraph.add_run(part)


def add_page_number_footer(section) -> None:
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            field = OxmlElement("w:fldChar")
            field.set(qn("w:fldCharType"), tag)
        else:
            field = OxmlElement("w:instrText")
            field.set(qn("xml:space"), "preserve")
            field.text = text
        run._r.append(field)


# --- Document parts ---

def setup_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    set_font(normal, FONT, 11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    for level, size in ((1, 16), (2, 13), (3, 12)):
        heading = doc.styles[f"Heading {level}"]
        set_font(heading, FONT, size)
        heading.font.bold = True
        heading.font.color.rgb = RGBColor(0x1F, 0x3A, 0x8A)
        heading.paragraph_format.space_before = Pt(14 if level == 1 else 10)
        heading.paragraph_format.space_after = Pt(6)
    for name in ("Title", "Subtitle", "Caption"):
        set_font(doc.styles[name], FONT)
    for section in doc.sections:
        section.left_margin = section.right_margin = Cm(2.5)
        section.top_margin = section.bottom_margin = Cm(2.2)


def add_title_page(doc: Document) -> None:
    def centered(text: str, size: float, bold=False, color=None, space_after=6):
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(space_after)
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color
        return paragraph

    for _ in range(6):
        doc.add_paragraph()
    centered(PROJECT_NAME, 24, bold=True, color=RGBColor(0x1F, 0x3A, 0x8A))
    centered(PROJECT_NAME_EN, 14, color=RGBColor(0x6B, 0x74, 0x89), space_after=18)
    centered(SUBTITLE, 18, bold=True, space_after=48)
    centered("Komanda", 13, bold=True)
    for name, role in TEAM:
        centered(f"{name} — {role}", 12, space_after=2)
    today = date.today()
    centered(f"{today.day} {MONTHS_AZ[today.month - 1]} {today.year}", 12, space_after=0).paragraph_format.space_before = Pt(48)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_code_block(doc: Document, lines: list[str]) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.left_indent = Cm(0.3)
    shade(paragraph._p, "F2F4F7")
    for i, line in enumerate(lines):
        run = paragraph.add_run(line)
        set_font(run, CODE_FONT, 9)
        if i < len(lines) - 1:
            run.add_break()


def add_table(doc: Document, rows: list[list[str]]) -> None:
    header, body = rows[0], rows[1:]
    table = doc.add_table(rows=1 + len(body), cols=len(header))
    table.style = "Table Grid"
    for r, cells in enumerate([header] + body):
        for c, text in enumerate(cells):
            cell = table.cell(r, c)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(2)
            add_inline(paragraph, text)
            if r == 0:
                for run in paragraph.runs:
                    run.bold = True
                shade(cell._tc, "E8EFFF")
    doc.add_paragraph()


def add_list_item(doc: Document, number: str | None, text: str):
    if number is None:
        paragraph = doc.add_paragraph(style="List Bullet")
    else:
        # Numbers are written as text: Word's auto-numbering would continue across lists.
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Cm(1.0)
        paragraph.paragraph_format.first_line_indent = Cm(-0.6)
        paragraph.add_run(f"{number}.\t")
        paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(1.0))
    paragraph.paragraph_format.space_after = Pt(3)
    add_inline(paragraph, text)
    return paragraph


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


# --- Markdown walk ---

def convert(markdown: str, doc: Document) -> None:
    lines = markdown.splitlines()
    i = 0
    skipped_title = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):  # fenced code block
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            add_code_block(doc, block)
            i += 1
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            if level == 1 and not skipped_title:  # the title is on the title page
                skipped_title = True
            else:
                add_inline(doc.add_heading("", level=max(1, level - 1)), text)
            i += 1
            continue

        if stripped.startswith("|"):  # table: header, separator, rows
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = table_cells(lines[i])
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            add_table(doc, rows)
            continue

        match = LIST_ITEM.match(stripped)
        if match and not line.startswith(" "):
            text = match.group(2)
            i += 1
            while i < len(lines) and lines[i].startswith(" ") and lines[i].strip():
                text += " " + lines[i].strip()  # indented continuation line
                i += 1
            add_list_item(doc, match.group(1), text)
            continue

        if not stripped or stripped == "---":
            i += 1
            continue

        text = stripped  # paragraph: consecutive plain lines
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^\s*(#|\||```|- |\d+\. |---$)", lines[i]):
            text += " " + lines[i].strip()
            i += 1
        add_inline(doc.add_paragraph(), text)


def add_screenshots(doc: Document) -> int:
    images = [p for p in SCREENSHOT_DIR.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")]
    order = list(SCREENSHOT_CAPTIONS)
    images.sort(key=lambda p: (order.index(p.stem) if p.stem in order else len(order), p.name))
    if not images:
        return 0
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading("Ekran şəkilləri", level=1)
    usable_width = doc.sections[-1].page_width - doc.sections[-1].left_margin - doc.sections[-1].right_margin
    for number, image in enumerate(images, start=1):
        picture = doc.add_paragraph()
        picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
        picture.paragraph_format.keep_with_next = True
        picture.add_run().add_picture(str(image), width=usable_width)
        caption = doc.add_paragraph(style="Caption")
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption.add_run(f"Şəkil {number}. {SCREENSHOT_CAPTIONS.get(image.stem, image.stem)}")
    return len(images)


def main(source: str, target: str) -> None:
    doc = Document()
    setup_styles(doc)
    add_page_number_footer(doc.sections[0])
    add_title_page(doc)
    convert(Path(source).read_text(encoding="utf-8"), doc)
    images = add_screenshots(doc)
    doc.core_properties.title = f"{PROJECT_NAME} — {SUBTITLE}"
    doc.core_properties.author = ", ".join(name for name, _ in TEAM)
    doc.save(target)
    print(f"Wrote {target} ({images} screenshots)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
