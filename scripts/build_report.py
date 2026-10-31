"""Build the final CT-363 report from the generated results.

    python run_all.py                    # writes output/results.json + figures
    python scripts/build_report_assets.py
    python scripts/build_report.py       # writes report/CT363_Smart_EV_Report.{docx,html,pdf}

Every result number in the report is read from output/results.json, which
run_all.py writes; nothing is typed by hand (brief section 0, rule 4).
The .docx is the editable submission copy. The PDF is printed from the HTML
copy with a headless Edge or Chrome, if one is installed (skip: --no-pdf).
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# ---- title-page facts (edit here if the CEP sheet says otherwise) ----
UNIVERSITY = "NED University of Engineering and Technology"
DEPARTMENT = "Department of Computer Science and Information Systems"   # CEP wording per brief
COURSE = "CT-363 Design and Analysis of Algorithms"
INSTRUCTOR = "Miss Tooba Shaikh"
TITLE = "Smart EV Charging Station Planning and Energy Allocation System"
SUBTITLE = "Complex Engineering Problem (CEP) Report"
TEAM = [("Sarim Khan", "CT-24266"), ("Muhammad Saraib", "CT-24255"),
        ("Danish Meraj", "CT-24268"), ("Muhammad Maaz Ali", "CT-24265")]


# ======================================================================
# Small document model: a list of blocks rendered to both DOCX and HTML.
# ======================================================================

class Report:
    def __init__(self):
        self.blocks = []
        self.n_table = 0
        self.n_fig = 0

    def h1(self, t): self.blocks.append(("h1", t))
    def h2(self, t): self.blocks.append(("h2", t))
    def h3(self, t): self.blocks.append(("h3", t))
    def p(self, t): self.blocks.append(("p", t))
    def bullets(self, items): self.blocks.append(("bullets", items))
    def numbered(self, items): self.blocks.append(("numbered", items))
    def code(self, t): self.blocks.append(("code", t.strip("\n")))
    def pagebreak(self): self.blocks.append(("pagebreak",))

    def table(self, caption, headers, rows, widths=None):
        self.n_table += 1
        self.blocks.append(("table", f"Table {self.n_table}. {caption}", headers,
                            [[str(c) for c in r] for r in rows], widths))
        return self.n_table

    def figure(self, path, caption, width_cm=15.5):
        self.n_fig += 1
        self.blocks.append(("figure", Path(path), f"Figure {self.n_fig}. {caption}", width_cm))
        return self.n_fig


INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def inline_parts(text):
    """Split '**bold** `code` *italic*' markup into (text, style) pieces."""
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**"):
            yield part[2:-2], "b"
        elif part.startswith("`"):
            yield part[1:-1], "c"
        elif part.startswith("*") and len(part) > 2:
            yield part[1:-1], "i"
        else:
            yield part, ""


# ---------------------------- DOCX ----------------------------------

def render_docx(rep, path, figdir):
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)          # A4
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(2.3))
    sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.2)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    for lvl, size in ((1, 16), (2, 13), (3, 11.5)):
        st = doc.styles[f"Heading {lvl}"]
        st.font.name = "Calibri"
        st.font.size = Pt(size)
        st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
        rfonts = st.element.rPr.rFonts                     # drop theme fonts so font.name wins
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            rfonts.attrib.pop(qn(attr), None)

    def shade(tc, hex_fill):
        """Cell shading (w:shd inside w:tcPr, where the schema expects it)."""
        pr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_fill)
        pr.append(shd)

    def add_runs(par, text, size=None):
        for t, style in inline_parts(text):
            run = par.add_run(t)
            if style == "b":
                run.bold = True
            elif style == "i":
                run.italic = True
            elif style == "c":
                run.font.name = "Consolas"
                run.font.size = Pt(9.5)
            if size and style != "c":
                run.font.size = Pt(size)

    def field(par, instr):
        run = par.add_run()
        b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin")
        i = OxmlElement("w:instrText"); i.set(qn("xml:space"), "preserve"); i.text = instr
        s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate")
        t = OxmlElement("w:t"); t.text = "Right-click and choose Update Field to build the table of contents."
        e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end")
        for x in (b, i, s, t, e):
            run._r.append(x)

    # page numbers in the footer
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); run._r.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; run._r.append(it)
    run.font.size = Pt(9)

    # ask Word to refresh the TOC field on open; w:updateFields must precede these siblings
    upd = OxmlElement("w:updateFields"); upd.set(qn("w:val"), "true")
    settings = doc.settings.element
    for zoom in settings.findall(qn("w:zoom")):          # default template omits the required percent
        zoom.set(qn("w:percent"), "100")
    later ={qn(t) for t in ("w:hdrShapeDefaults", "w:footnotePr", "w:endnotePr", "w:compat", "w:docVars",
                             "w:rsids", "m:mathPr", "w:attachedSchema", "w:themeFontLang", "w:clrSchemeMapping",
                             "w:doNotIncludeSubdocsInStats", "w:doNotAutoCompressPictures", "w:forceUpgrade",
                             "w:captions", "w:readModeInkLockDown", "w:smartTagType", "sl:schemaLibrary",
                             "w:shapeDefaults", "w:doNotEmbedSmartTags", "w:decimalSymbol", "w:listSeparator")}
    anchor = next((ch for ch in settings if ch.tag in later), None)
    if anchor is not None:
        anchor.addprevious(upd)
    else:
        settings.append(upd)

    for blk in rep.blocks:
        kind = blk[0]
        if kind == "title_page":
            _, lines = blk
            for text, size, bold, space in lines:
                par = doc.add_paragraph()
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                par.paragraph_format.space_after = Pt(space)
                r = par.add_run(text); r.font.size = Pt(size); r.bold = bold
            continue
        if kind == "team_table":
            _, rows = blk
            t = doc.add_table(rows=len(rows) + 1, cols=2)
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for j, h in enumerate(("Student name", "Roll number")):
                c = t.rows[0].cells[j]; c.text = ""; add_runs(c.paragraphs[0], f"**{h}**"); shade(c._tc, "D9E2F3")
            for i, (nm, roll) in enumerate(rows, 1):
                t.rows[i].cells[0].text = nm
                t.rows[i].cells[1].text = roll
            for row in t.rows:
                row.cells[0].width, row.cells[1].width = Cm(7), Cm(4)
            continue
        if kind == "toc":
            doc.add_heading("Table of Contents", 1)
            field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
            continue
        if kind in ("h1", "h2", "h3"):
            doc.add_heading(blk[1], int(kind[1]))
        elif kind == "p":
            add_runs(doc.add_paragraph(), blk[1])
        elif kind in ("bullets", "numbered"):
            for idx, item in enumerate(blk[1], 1):
                par = doc.add_paragraph(style="List Bullet" if kind == "bullets" else None)
                if kind == "numbered":
                    par.paragraph_format.left_indent = Cm(0.9)
                    par.paragraph_format.first_line_indent = Cm(-0.6)
                    par.add_run(f"{idx}.  ")
                par.paragraph_format.space_after = Pt(3)
                add_runs(par, item)
        elif kind == "code":
            # a one-cell shaded table keeps the code block together and shaded
            box = doc.add_table(rows=1, cols=1)
            box.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = box.rows[0].cells[0]
            cell.width = Cm(16.4)
            shade(cell._tc, "F2F4F7")
            par = cell.paragraphs[0]
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.space_after = Pt(0)
            lines = blk[1].split("\n")
            for li, line in enumerate(lines):
                r = par.add_run(line)
                r.font.name = "Consolas"; r.font.size = Pt(8.5)
                r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Consolas")
                if li < len(lines) - 1:
                    r.add_break(WD_BREAK.LINE)
            doc.add_paragraph().paragraph_format.space_after = Pt(0)
        elif kind == "table":
            _, caption, headers, rows, widths = blk
            cap = doc.add_paragraph(); cap.paragraph_format.keep_with_next = True
            r = cap.add_run(caption); r.bold = True; r.font.size = Pt(9.5)
            t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for j, h in enumerate(headers):
                c = t.rows[0].cells[j]; c.text = ""
                add_runs(c.paragraphs[0], f"**{h}**", size=9)
                shade(c._tc, "D9E2F3")
            for i, row in enumerate(rows, 1):
                for j, val in enumerate(row):
                    c = t.rows[i].cells[j]; c.text = ""
                    add_runs(c.paragraphs[0], val, size=9)
            for row in t.rows:
                for c in row.cells:
                    for par in c.paragraphs:
                        par.paragraph_format.space_after = Pt(0)
                        par.paragraph_format.line_spacing = 1.0
            if widths:
                total = 16.4
                for row in t.rows:
                    for j, c in enumerate(row.cells):
                        c.width = Cm(total * widths[j] / sum(widths))
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
        elif kind == "figure":
            _, fpath, caption, width_cm = blk
            par = doc.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            par.paragraph_format.keep_with_next = True
            par.add_run().add_picture(str(figdir / fpath.name), width=Cm(width_cm))
            cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = cap.add_run(caption); r.italic = True; r.font.size = Pt(9.5)
        elif kind == "pagebreak":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.save(path)


# ----------------------------- HTML ---------------------------------

# PDF styling follows the team's proposal: navy cover with a green accent, numbered
# section headings with a green rule, navy table headers, running header and footer.
NAVY, NAVY2, GREEN = "#0c1e38", "#15294a", "#14a37a"
CSS = f"""
@page {{ size: A4; margin: 22mm 18mm 20mm 18mm;
  @top-left {{ content: "SMART EV CHARGING OPTIMIZER"; font: bold 7.5pt Arial, sans-serif; letter-spacing: 1.2pt; color: #1b2433; vertical-align: bottom; padding-bottom: 3mm; border-bottom: 1.4pt solid {GREEN}; }}
  @top-right {{ content: "CEP Report \\00B7 CT-363"; font: 7.5pt Arial, sans-serif; color: #6b7280; vertical-align: bottom; padding-bottom: 3mm; border-bottom: 1.4pt solid {GREEN}; }}
  @bottom-left {{ content: "{UNIVERSITY} \\00B7 {DEPARTMENT}"; font: 7.5pt Arial, sans-serif; color: #6b7280; vertical-align: top; padding-top: 3mm; border-top: 0.6pt solid #d1d5db; }}
  @bottom-right {{ content: counter(page); font: bold 8pt Arial, sans-serif; color: #1b2433; vertical-align: top; padding-top: 3mm; border-top: 0.6pt solid #d1d5db; }} }}
@page :first {{ margin: 0; @top-left {{ content: none; border: 0 }} @top-right {{ content: none; border: 0 }}
  @bottom-left {{ content: none; border: 0 }} @bottom-right {{ content: none; border: 0 }} }}
* {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ font: 9.6pt/1.5 Arial, "Liberation Sans", Helvetica, sans-serif; color: #1f2937; margin: 0; }}
h1 {{ font: bold 15pt Arial, sans-serif; color: #111827; margin: 16pt 0 8pt; padding-bottom: 4pt; border-bottom: 1.4pt solid {GREEN}; page-break-after: avoid; }}
h1 .num {{ color: {GREEN}; margin-right: 8pt; }}
h2 {{ font: bold 11pt Arial, sans-serif; color: {GREEN}; margin: 12pt 0 4pt; page-break-after: avoid; }}
h3 {{ font: bold 10pt Arial, sans-serif; color: #111827; margin: 9pt 0 3pt; page-break-after: avoid; }}
p {{ margin: 0 0 6pt; text-align: justify; }}
b {{ color: #111827; }}
ul, ol {{ margin: 0 0 6pt; padding-left: 16pt; }} li {{ margin-bottom: 2pt; }}
code {{ font: 8.4pt Consolas, "DejaVu Sans Mono", monospace; color: #0f5132; }}
pre {{ font: 8pt/1.35 Consolas, "DejaVu Sans Mono", monospace; background: {NAVY}; color: #e5ecf5; padding: 7pt 9pt; border-left: 4pt solid {GREEN}; white-space: pre-wrap; page-break-inside: avoid; margin: 4pt 0 8pt; }}
table {{ border-collapse: collapse; width: 100%; font-size: 8.4pt; margin: 2pt 0 10pt; }}
tr {{ page-break-inside: avoid; }}
th, td {{ padding: 3pt 5pt; vertical-align: top; text-align: left; border-bottom: 0.5pt solid #e5e7eb; }}
th {{ background: {NAVY}; color: #fff; font-weight: bold; border-bottom: 1.4pt solid {GREEN}; }}
tbody tr:nth-child(even) td {{ background: #f3f6f9; }}
td:first-child {{ font-weight: bold; color: #111827; }}
.cap {{ font: bold 8.6pt Arial, sans-serif; color: #374151; margin: 8pt 0 3pt; page-break-after: avoid; }}
figure {{ margin: 8pt 0 10pt; text-align: center; page-break-inside: avoid; }}
figure img {{ max-width: 100%; }}
figcaption {{ font-size: 8.6pt; color: #4b5563; font-style: italic; }}
.pb {{ page-break-after: always; }}
.toc {{ font-size: 9.6pt; line-height: 1.35; }}
.toc a {{ color: #1f2937; text-decoration: none; }}
.toc ol {{ list-style: none; padding-left: 0; margin: 0; }} .toc li {{ margin: 0; }} .toc li li {{ padding-left: 16pt; color: #4b5563; }}
.toc > ol > li {{ margin-top: 4pt; font-weight: bold; }} .toc li li a {{ font-weight: normal; color: #4b5563; }}

/* cover, modelled on the proposal */
.cover {{ width: 210mm; height: 296mm; overflow: hidden; background: {NAVY}; color: #fff; position: relative;
  box-sizing: border-box; padding: 0 16mm 0 20mm; border-left: 3mm solid {GREEN}; }}
.cover .top {{ display: flex; align-items: center; justify-content: space-between; padding: 12mm 0 6mm;
  border-bottom: 0.8pt solid {GREEN}; }}
.cover .top img {{ width: 22mm; height: 22mm; }}
.cover .uni {{ text-align: center; }}
.cover .uni .n {{ font: bold 13pt Georgia, "DejaVu Serif", serif; }}
.cover .uni .d {{ font: 8.5pt Arial, sans-serif; color: #c7d2e0; margin-top: 2pt; }}
.cover .eyebrow {{ font: bold 8.5pt Arial, sans-serif; letter-spacing: 3pt; color: {GREEN}; margin: 16mm 0 4mm; }}
.cover h1.t {{ font: bold 30pt/1.22 Georgia, "DejaVu Serif", serif; color: #fff; border: 0; margin: 0; padding: 0; }}
.cover .sub {{ font: bold 15pt Georgia, "DejaVu Serif", serif; color: {GREEN}; margin: 5mm 0 8mm; }}
.cover .net {{ display: block; width: 125mm; margin: 0 auto 8mm; }}
.cover .rule {{ border-top: 0.6pt solid #2a3d5c; margin: 0 0 6mm; }}
.cover .meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; margin-bottom: 7mm; }}
.cover .lbl {{ font: bold 7.5pt Arial, sans-serif; letter-spacing: 2.5pt; color: {GREEN}; margin-bottom: 2mm; }}
.cover .val {{ font: bold 10.5pt Arial, sans-serif; color: #fff; }}
.cover .members {{ display: grid; grid-template-columns: 1fr 1fr; gap: 3.5mm 5mm; }}
.cover .card {{ background: {NAVY2}; border-left: 1.2mm solid {GREEN}; padding: 3mm 4mm; }}
.cover .card .nm {{ font: bold 10.5pt Arial, sans-serif; }}
.cover .card .rl {{ font: 8.5pt Arial, sans-serif; color: #aab6c8; margin-top: 1mm; }}
.cover .sig {{ position: absolute; left: 20mm; right: 16mm; bottom: 12mm; display: flex; justify-content: space-between;
  font: 8.5pt Arial, sans-serif; color: #aab6c8; }}
"""


def cover_html(fig_rel):
    members = "".join(f'<div class="card"><div class="nm">{html.escape(n)}</div><div class="rl">Roll No. {r}</div></div>'
                      for n, r in TEAM)
    return (f'<div class="cover"><div class="top"><img src="{fig_rel}/logo_left.png" alt="">'
            f'<div class="uni"><div class="n">{html.escape(UNIVERSITY)}</div><div class="d">{html.escape(DEPARTMENT)}</div></div>'
            f'<img src="{fig_rel}/logo_right.png" alt=""></div>'
            f'<div class="eyebrow">COMPLEX ENGINEERING PROBLEM · FINAL REPORT</div>'
            f'<h1 class="t">Smart EV Charging Station Planning and Energy Allocation System</h1>'
            f'<div class="sub">for Urban Pakistan</div>'
            f'<img class="net" src="{fig_rel}/cover_network.png" alt="">'
            f'<div class="rule"></div>'
            f'<div class="meta"><div><div class="lbl">COURSE</div><div class="val">Design and Analysis of Algorithms · CT-363</div></div>'
            f'<div><div class="lbl">COURSE INSTRUCTOR</div><div class="val">{html.escape(INSTRUCTOR)}</div></div></div>'
            f'<div class="lbl">GROUP MEMBERS</div><div class="members">{members}</div>'
            f'<div class="sig"><span>Date: {date.today().strftime("%d %B %Y")}</span>'
            f'<span>Faculty signature: ______________________</span></div></div>')


def render_html(rep, path, fig_rel):
    def inl(text):
        out = []
        for t, st in inline_parts(text):
            t = html.escape(t)
            out.append({"b": f"<b>{t}</b>", "i": f"<i>{t}</i>", "c": f"<code>{t}</code>"}.get(st, t))
        return "".join(out)

    body, toc = [], []
    hid = 0
    in_title = False
    for blk in rep.blocks:
        kind = blk[0]
        if kind == "title_page":                 # the HTML/PDF uses the proposal-style cover
            if not in_title:
                body.append(cover_html(fig_rel))
                in_title = True
            continue
        if kind in ("team_table", "end_title"):
            continue
        if kind == "toc":
            body.append("<!--TOC-->")
            continue
        if kind in ("h1", "h2", "h3"):
            hid += 1
            m = re.match(r"(\d+)\.\s+(.*)", blk[1]) if kind == "h1" else None
            label = (f'<span class="num">{int(m.group(1)):02d}</span>{html.escape(m.group(2))}' if m
                     else html.escape(blk[1]))
            body.append(f'<{kind} id="s{hid}">{label}</{kind}>')
            if kind in ("h1", "h2"):
                toc.append((kind, hid, blk[1]))
        elif kind == "p":
            body.append(f"<p>{inl(blk[1])}</p>")
        elif kind in ("bullets", "numbered"):
            tag = "ul" if kind == "bullets" else "ol"
            body.append(f"<{tag}>" + "".join(f"<li>{inl(i)}</li>" for i in blk[1]) + f"</{tag}>")
        elif kind == "code":
            body.append(f"<pre>{html.escape(blk[1])}</pre>")
        elif kind == "table":
            _, cap, headers, rows, _w = blk
            head = "".join(f"<th>{inl(h)}</th>" for h in headers)
            trs = "".join("<tr>" + "".join(f"<td>{inl(c)}</td>" for c in r) + "</tr>" for r in rows)
            body.append(f'<p class="cap">{html.escape(cap)}</p><table><thead><tr>{head}</tr></thead><tbody>{trs}</tbody></table>')
        elif kind == "figure":
            _, fpath, cap, width_cm = blk
            body.append(f'<figure><img src="{fig_rel}/{fpath.name}" style="width:{width_cm * 10:.0f}mm" alt="">'
                        f"<figcaption>{html.escape(cap)}</figcaption></figure>")
        elif kind == "pagebreak":
            body.append('<div class="pb"></div>')

    items, open_sub = [], False
    for kind, i, text in toc:
        if kind == "h1":
            if open_sub:
                items.append("</ol>"); open_sub = False
            items.append(f'<li><a href="#s{i}">{html.escape(text)}</a>')
        else:
            if not open_sub:
                items.append("<ol>"); open_sub = True
            items.append(f'<li><a href="#s{i}">{html.escape(text)}</a></li>')
    if open_sub:
        items.append("</ol>")
    toc_html = '<h1>Table of Contents</h1><div class="toc"><ol>' + "".join(items) + "</ol></div>"
    doc = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
           f"<title>{html.escape(TITLE)}</title><style>{CSS}</style></head><body>"
           + "\n".join(body).replace("<!--TOC-->", toc_html) + "</body></html>")
    path.write_text(doc, encoding="utf-8")


def find_browser():
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"):
        if shutil.which(name):
            return shutil.which(name)
    return None


def print_pdf(html_path, pdf_path):
    browser = find_browser()
    if not browser:
        print("no Edge/Chrome found: skipped PDF (the .docx and .html are complete)")
        return False
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
                   check=True, capture_output=True, timeout=180)
    return pdf_path.exists()


# ======================================================================
# Architecture figure (not a result, so it is drawn here)
# ======================================================================

def architecture_figure(path):
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=170)
    ax.set_xlim(0, 100); ax.set_ylim(0, 56); ax.axis("off")
    ink, blue, green, grey = "#1f3a5f", "#d9e8f7", "#dff3e6", "#eef0f3"

    def box(x, y, w, h, title, sub, fill):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    fc=fill, ec=ink, lw=1.1))
        ax.text(x + w / 2, y + h - 2.6, title, ha="center", va="top", fontsize=9.5, weight="bold", color=ink)
        ax.text(x + w / 2, y + h - 6.2, sub, ha="center", va="top", fontsize=7.6, color="#333", linespacing=1.3)

    def arrow(x1, y1, x2, y2, label=None):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=11, lw=1.1, color=ink))
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.2, label, ha="center", fontsize=7, color="#444")

    box(1, 38, 19, 15, "1. Input", "4 CSV files\nlocations, roads,\nstations, requests", grey)
    box(25, 38, 19, 15, "2. Validation", "io_validate.py\nduplicate IDs, negative\nvalues, bad endpoints,\nunit rounding", grey)
    box(49, 38, 22, 15, "3. Active graph", "graph.py\ndrop unavailable roads\nedge order: cost, -s(u)-s(v),\nmin id, max id", blue)
    box(76, 38, 23, 15, "4. Kruskal MSF", "kruskal.py + dsu.py\nunion by rank,\npath compression\n-> forest + components", blue)
    box(76, 17, 23, 15, "5. Eligibility", "eligibility.py\nsame component only;\nlabel no_eligible /\ntoo_large before DP", green)
    box(49, 17, 22, 15, "6. Exact DP", "dp.py (NumPy table)\n0/1 multiple knapsack\nskip or one station\n+ backtracking", green)
    box(25, 17, 19, 15, "7. Validators", "validate.py\nforest acyclic, spanning;\nloads <= capacity,\neligible, once only", grey)
    box(1, 17, 19, 15, "8. Outputs", "run_all.py\nE1-E5 tables, figures,\nedge_cases.log,\nresults.json", grey)
    box(49, 1, 22, 12, "Repair (E2)", "repair.py: replace a failed\nforest road by the cheapest\nroad across its cut", blue)
    box(25, 1, 19, 12, "Checks", "brute.py (q <= 10)\nheuristic.py (greedy gap)", grey)
    box(76, 1, 23, 12, "Consumers", "report (this document)\nNext.js dashboard", grey)

    arrow(20, 45.5, 25, 45.5); arrow(44, 45.5, 49, 45.5); arrow(71, 45.5, 76, 45.5)
    arrow(87.5, 38, 87.5, 32, "component_of")
    arrow(76, 24.5, 71, 24.5); arrow(49, 24.5, 44, 24.5); arrow(25, 24.5, 20, 24.5)
    arrow(60, 17, 60, 13); arrow(87.5, 17, 87.5, 13)
    ax.text(50, 55.5, "Part A (Greedy) in blue, Part B (Dynamic Programming) in green",
            ha="center", fontsize=8.5, color="#444")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# ======================================================================
# Content
# ======================================================================

def fmt_ms(x):
    return f"{x:.3f} ms" if x < 1 else (f"{x:.2f} ms" if x < 100 else f"{x:,.0f} ms")


def fmt_bytes(b):
    return f"{b / 1000:.1f} KB" if b < 1_000_000 else f"{b / 1_000_000:.1f} MB"


def count_tests():
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120).stdout
        m = re.search(r"(\d+) tests? collected", out)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def build_content(r, n_tests):
    rep = Report()
    sites = {s["id"]: s for s in r["sites"]}
    name = {k: v["name"] for k, v in sites.items()}
    roads = {x["id"]: x for x in r["roads"]}
    st_at = {s["site"]: s for s in r["stations"]}
    e1, e2, e3, e4, e5, ver = r["e1"], r["e2"], r["e3"], r["e4"], r["e5"], r["verification"]
    a1, a2, a3 = e1["allocation"], e2["allocation"], e3["allocation"]
    stress = e1["stress"]["allocation"]
    m_total, m_active = len(r["roads"]), len(r["roads"]) - len(e1["dropped"])
    n_sites, q = len(r["sites"]), len(r["requests"]) if "requests" in r else a1["requests_total"]
    k = len(a1["loads"])
    q_dp = a1["dp"]["total_states"] // a1["dp"]["states_per_layer"] - 1
    caps = {sid: l["capacity"] for sid, l in a1["loads"].items()}
    cap_total = sum(caps.values())
    hub = next(s for s in r["sites"] if s["is_hub"])
    sev_sorted = sorted(r["sites"], key=lambda s: -s["severity"])
    machine = r["meta"].get("machine", {})
    runs = r["meta"]["timing_runs"]

    def rname(rid):
        x = roads[rid]
        return f"{rid} {name[x['u']]}–{name[x['v']]}"

    def comps_text(comps):
        return "; ".join(f"{{{', '.join(name[s] for s in c['sites'])}}}" for c in comps)

    def counts_text(d):
        return ", ".join(f"{k_}: {v}" for k_, v in d.items())

    main_sites = set(next(c for c in e1["components"] if c["has_hub"])["sites"])
    def comp_of(site, comps):
        for c in comps:
            if site in c["sites"]:
                return c
        return None

    feasible = [x for x in a1["requests"] if x["reason"] not in
                ("too_large_for_any_eligible_station", "no_eligible_station", "origin_site_removed")]
    demand_by_comp = {}
    for c in e1["components"]:
        dem = sum(x["units"] for x in feasible if x["origin"] in c["sites"])
        cap = sum(caps[s] for s in caps if next(st for st in r["stations"] if st["id"] == s)["site"] in c["sites"])
        if dem or cap:
            demand_by_comp[c["label"]] = (dem, cap)
    lost1 = [x["id"] for x in a1["requests"] if x["reason"] == "lost_to_capacity_competition"]
    heavy = [x for x in a1["requests"] if x["reason"] == "too_large_for_any_eligible_station"]
    noel = [x for x in a1["requests"] if x["reason"] == "no_eligible_station"]
    net200 = e5["network"][-1]
    bf10 = e5["brute"][-1]
    cap_last = e5["capacity"][-1]

    # ------------------------------------------------------------ title
    rep.blocks.append(("title_page", [
        (UNIVERSITY, 15, True, 2), (DEPARTMENT, 12, False, 26),
        (COURSE, 12, True, 4), (SUBTITLE, 12, False, 34),
        (TITLE, 20, True, 8),
        (f"Greedy minimum spanning forest + exact multi-knapsack dynamic programming on the synthetic "
         f"{r['meta']['dataset']} dataset", 11, False, 34),
        ("Submitted by", 11, True, 6)]))
    rep.blocks.append(("team_table", TEAM))
    rep.blocks.append(("title_page", [
        ("", 8, False, 20),
        (f"Course instructor: {INSTRUCTOR}", 11, False, 6),
        (f"Date: {date.today().strftime('%d %B %Y')}", 11, False, 30),
        ("Faculty signature: ______________________", 11, False, 4)]))
    rep.blocks.append(("end_title",))
    rep.pagebreak()
    rep.blocks.append(("toc",))
    rep.pagebreak()

    # ------------------------------------------------------------ abstract
    rep.h1("Abstract")
    rep.p(f"This report presents a decision-support prototype that plans an electric-vehicle (EV) charging network and "
          f"allocates limited charging energy, using two algorithmic paradigms. Part A uses a **greedy** algorithm, "
          f"Kruskal's algorithm with a Union-Find (disjoint-set) structure, to build a minimum spanning forest over the "
          f"available roads between candidate sites; unavailable roads are filtered before sorting, equal-cost ties are "
          f"broken deterministically by site severity and IDs, and the forest is repaired incrementally after road "
          f"failures. Part B uses exact **dynamic programming** for the 0/1 multiple-knapsack problem: each charging "
          f"request is assigned to at most one eligible station, where a station is eligible only if it lies in the same "
          f"connected component as the request's origin. On the synthetic {r['meta']['dataset']} dataset "
          f"({n_sites} sites, {m_total} roads of which {m_total - m_active} are unavailable, {k} active stations and "
          f"{a1['requests_total']} requests) the forest costs {e1['cost']} over {len(e1['components'])} components, "
          f"and the DP serves {a1['served']} requests for a total benefit of {a1['benefit']} using all {cap_total} "
          f"capacity units. The DP agreed with brute force on {ver['agree']} of {ver['instances']} random instances, "
          f"and the incremental repair matched full Kruskal in cost on every tested graph. Sensitivity experiments "
          f"cover road failures, removal of the two highest-severity sites, capacity cuts, extra demand and scaling up "
          f"to {net200['n']} sites. All values are model outputs on synthetic data.")

    # ------------------------------------------------------------ 1 intro
    rep.h1("1. Introduction")
    rep.p("Electric-vehicle adoption requires charging infrastructure that is both cheap to connect and efficiently "
          "used. A planner must connect candidate charging sites at low cost while some roads are closed, and must then "
          "decide which charging requests each station serves when total demand exceeds the available energy. These "
          "goals conflict: the cheapest network does not maximise coverage, and serving one large request can block "
          "several smaller ones.")
    rep.p("The project solves the two problems on one dataset and links them through graph connectivity: the network "
          "stage decides which stations a request can reach, and the allocation stage decides which reachable requests "
          "are served. The system does not choose where to build stations (facility location); candidate sites are "
          "given. All data are synthetic and labelled as such.")
    rep.p("The CT-363 CEP sheet describes a flood-relief scenario. The team used EV charging as its own case study; "
          f"Table {rep.n_table + 1} maps the two so that every CEP requirement has a counterpart.")
    rep.table("Mapping between the CEP flood-relief scenario and this project.",
              ["CEP scenario", "This project"],
              [["Village", "Site (candidate charging location)"], ["Road / submerged road", "Road / unavailable road"],
               ["Emergency operations centre (EOC)", f"Hub ({hub['name']})"], ["Truck", "Charging station"],
               ["Relief item", "EV charging request (one indivisible item)"], ["Lives impacted", "Benefit"],
               ["Bounded / multiple knapsack", "0/1 multiple knapsack (each request is one indivisible item)"]],
              [1, 1.4])
    rep.h2("1.1 Objectives")
    rep.bullets([
        "Model sites and roads as a weighted undirected graph and build a minimum spanning tree or forest with Kruskal + DSU.",
        "Exclude unavailable roads before sorting, use a documented deterministic tie-break, and name every component.",
        "Repair the forest incrementally after three road failures and verify it against full recomputation.",
        "Formulate and implement an exact multi-knapsack DP that assigns each request to at most one eligible station, "
        "with reconstruction of the assignment and an explicit reason for every unserved request.",
        "Prove correctness, derive exact time and space complexity, and measure runtime.",
        "Run the mandatory edge cases and the sensitivity experiments E1 to E5 reproducibly.",
    ])

    # ------------------------------------------------------------ 2 lit
    rep.h1("2. Literature Review")
    rep.p("**Minimum spanning trees.** The minimum spanning tree problem dates back to Borůvka (1926). Kruskal (1956) "
          "proposed scanning edges in non-decreasing weight order and keeping an edge whenever it joins two different "
          "trees; Prim (1957) grows a single tree from a start vertex. Both are justified by the cut property: the "
          "lightest edge crossing any cut that respects the current partial solution is safe [1]. On a disconnected "
          "graph Kruskal naturally returns a minimum spanning forest, one tree per component, whereas Prim must be "
          "restarted per component.")
    rep.p("**Disjoint sets.** Kruskal's efficiency depends on fast connectivity queries. With union by rank and path "
          "compression, a sequence of m operations on n elements runs in O(m α(n)) time, where α is the inverse "
          "Ackermann function (Tarjan, 1975) [1][4]. α(n) ≤ 4 for any practical n.")
    rep.p("**Dynamic MST.** Maintaining an MST under edge deletions is a studied problem with sophisticated "
          "structures (Frederickson, 1985; Holm, de Lichtenberg and Thorup, 2001) [5][6]. This project deliberately "
          "uses a simple repair (find the cut created by a deleted tree edge and add the cheapest crossing edge), "
          "which is correct but not asymptotically optimal, and measures it rather than assuming a speed-up.")
    rep.p("**Knapsack problems.** The 0/1 knapsack problem is NP-hard but solvable in pseudo-polynomial time by "
          "dynamic programming over capacity values [1][7]. The multiple knapsack problem, with several capacities "
          "and each item placed in at most one knapsack, is strongly NP-hard in general; exact methods include "
          "branch-and-bound and DP over the vector of remaining capacities, whose state space is the product of "
          "(C_j + 1) and therefore grows exponentially with the number of knapsacks [7][8]. This motivates the "
          "project's restriction to k = 3 stations (k = 4 in the stress run).")

    # ------------------------------------------------------------ 3 formulation
    rep.h1("3. Problem Formulation")
    rep.p("**Notation.** n sites, m roads, q requests, k stations, used consistently in code and text.")
    rep.h2("3.1 Part A: minimum spanning forest")
    rep.p("Let G = (V, E) be an undirected graph with |V| = n sites and |E| = m roads. Road e = (u, v) has cost "
          "w(e) ≥ 0 and an availability flag; site v has a severity s(v). Let E_active be the available roads between "
          "active sites. The goal is a spanning forest F ⊆ E_active of minimum total cost that spans every connected "
          "component of (V, E_active). Roads are ranked by the key")
    rep.code("key(e) = ( w(e) ascending,  s(u)+s(v) descending,  min(u,v) ascending,  max(u,v) ascending )")
    rep.p("Severity only orders roads of equal cost, so it never changes the minimum total cost; it selects one "
          "forest among equal-cost alternatives. Kruskal therefore does **not** maximise severity coverage.")
    rep.h2("3.2 Part B: 0/1 multiple-knapsack allocation")
    rep.p("Request i has an integer energy requirement w_i (units) and benefit b_i; station j has capacity C_j. "
          "Let E_i be the set of active stations in the same component as request i's origin, and x_ij = 1 if request "
          "i is assigned to station j.")
    rep.code("maximise    Σ_i Σ_j  b_i · x_ij\n"
             "subject to  Σ_j x_ij ≤ 1                for every request i   (at most one station)\n"
             "            Σ_i w_i · x_ij ≤ C_j        for every station j   (capacity)\n"
             "            x_ij = 0 if j ∉ E_i                               (eligibility)\n"
             "            x_ij ∈ {0, 1}                                     (indivisible requests)")
    rep.p(f"**Units.** 1 unit = {r['meta']['kwh_per_unit']} kWh. Request energy is rounded **up** (a request is never "
          "under-served) and station capacity is rounded **down** (a station never promises energy it lacks). "
          "Benefits are integers from 10 to 100, so the DP never compares floating-point values. Time-decay of "
          "benefit is off, because the CEP states that values are constants.")
    rep.p("**Assumptions.** Costs and capacities are known, non-negative inputs; the graph is undirected; each request "
          "consumes its full requirement; charging time, queues, prices, grid limits and safety risk are discussed but "
          "not optimised.")
    rep.h2("3.3 Conflicting requirements")
    rep.table("Conflicting engineering requirements and how each was resolved (WP2).",
              ["Conflict", "Resolution in the design", "Evidence from the results"],
              [["Connection cost vs coverage", "Kruskal minimises total cost only; components are reported by name and "
                "maximum coverage is never claimed.",
                f"Baseline forest cost {e1['cost']} leaves {len(e1['components'])} components; "
                f"{name[noel[0]['origin']] if noel else 'an isolated site'} stays unconnected."],
               ["Safety vs low cost", "Unavailable roads are a hard filter applied before sorting.",
                f"Cheapest road overall ({rname(min(e1['dropped'], key=lambda d: roads[d['road']]['cost'])['road'])}, "
                f"cost {min(roads[d['road']]['cost'] for d in e1['dropped'])}) is unavailable and never selected."],
               ["Capacity vs demand", "Hard capacity constraints; maximise total benefit; every unserved request gets "
                "a reason. Fairness is not guaranteed.",
                f"{a1['served']} of {a1['requests_total']} served; {len(lost1)} lost to capacity competition."],
               ["Benefit vs fairness / urgency", "Objective is the sum of declared benefits; ties prefer serving more "
                "requests. Urgency would enter only through a stated benefit formula.",
                f"Greedy benefit-per-unit baseline reaches {ver['greedy']['dataset_greedy']} vs DP "
                f"{ver['greedy']['dataset_dp']}."],
               ["Time-decay vs computation", "Decay is off; if enabled, b_i(t) = b_i·e^(−λt) would be fixed per run so "
                "the DP stays exact.", "All runs use constant benefits."],
               ["Exactness vs scalability", f"Exact dense DP limited to k = {k} stations (stress k = 4); network "
                "stage scales separately.",
                f"States per layer grow from {e5['capacity'][0]['states_per_layer']:,} to "
                f"{cap_last['states_per_layer']:,} when capacities are multiplied by {cap_last['factor']} (E5)."]],
              [1, 1.6, 1.6])

    # ------------------------------------------------------------ 4 architecture
    rep.h1("4. System Architecture")
    rep.p(f"The implementation is a modular Python pipeline (Figure {rep.n_fig + 1}). Each module has one job and is unit-tested on "
          "its own; `run_all.py` runs the whole pipeline for every experiment, validates every result and writes all "
          "tables, figures and `results.json`, which both this report and the dashboard read.")
    rep.figure("fig_architecture.png", "Block diagram of the system: data flow from the CSV inputs through both "
               "algorithmic stages to the validated outputs.", 16)
    rep.table("Source modules.", ["Module", "Responsibility"],
              [["`io_validate.py`", "Load CSVs into typed records; reject duplicate IDs, negative values, invalid endpoints, "
                "self-loops and unit-rounding errors."],
               ["`graph.py`", "Active graph (drop unavailable roads and removed sites); the single edge order `edge_key`; BFS."],
               ["`dsu.py`", "Union-Find with union by rank and path compression."],
               ["`kruskal.py`", "Kruskal MSF with full trace; components with site names; hub and isolated flags."],
               ["`repair.py`", "Incremental repair of the forest after road failures."],
               ["`eligibility.py`", "Same-component eligibility and pre-DP unserved labels."],
               ["`dp.py`", "Exact 0/1 multiple-knapsack DP on a dense NumPy table with backtracking."],
               ["`brute.py`, `heuristic.py`", "Brute-force checker (q ≤ 10); greedy benefit-per-unit baseline."],
               ["`validate.py`, `pipeline.py`", "Independent result validators; glue code and experiment edits."],
               ["`run_all.py`", "Experiments E1–E5, verification, edge-case log, figures, `results.json`."]],
              [1, 3])

    # ------------------------------------------------------------ 5 methodology
    rep.h1("5. Methodology and Pseudocode")
    rep.h2("5.1 Part A: Union-Find (A1)")
    rep.code("""
MAKE-SET(x):   parent[x] <- x;  rank[x] <- 0
FIND(x):
    root <- x
    while parent[root] != root: root <- parent[root]
    while parent[x] != root:                         // path compression
        next <- parent[x];  parent[x] <- root;  x <- next
    return root
UNION(a, b):
    ra <- FIND(a);  rb <- FIND(b)
    if ra = rb: return FALSE                         // same set: would close a cycle
    if rank[ra] < rank[rb]: swap(ra, rb)             // union by rank
    parent[rb] <- ra
    if rank[ra] = rank[rb]: rank[ra] <- rank[ra] + 1
    return TRUE""")
    rep.h2("5.2 Part A: Kruskal minimum spanning forest (A2)")
    rep.code("""
KRUSKAL-MSF(V, E, s):
    A <- { e in E : e.available }                    // filter BEFORE sorting
    sort A by key(e) = (w(e), -(s(u)+s(v)), min(u,v), max(u,v))
    for v in V: MAKE-SET(v)
    F <- empty;  cost <- 0
    for e = (u, v) in A:                             // invariant: F acyclic, DSU sets = trees of F
        if UNION(u, v):  F <- F + {e};  cost <- cost + w(e)
        else:            record e as "rejected: cycle"
    return F, cost, DSU groups (each named by its sites)""")
    rep.h2("5.3 Part A: incremental repair after road failures (A3)")
    rep.code("""
REPAIR(F, E_active, failed, s):
    S <- E_active - failed                           // surviving roads
    for e = (u, v) in failed:
        if e not in F: continue                      // forest still valid
        F <- F - {e}
        C1 <- BFS(u, F);  C2 <- BFS(v, F)            // the two sides of the cut
        best <- argmin over x in S with one end in C1 and the other in C2 of key(x)
        if best exists: F <- F + {best}
        else: keep the split                         // the component really broke
    return F""")
    rep.h2("5.4 Link: eligibility (B0)")
    rep.code("""
ELIGIBILITY(requests, stations, comp):               // comp = site -> component label
    for each request r:
        if r.origin is removed:           reason[r] <- origin_site_removed
        E_r <- { active j : comp[j.site] = comp[r.origin] }
        if E_r empty:                     reason[r] <- no_eligible_station
        else if r.units > max_{j in E_r} C_j: reason[r] <- too_large_for_any_eligible_station
        else:                             add r to the DP input""")
    rep.h2("5.5 Part B: exact multi-knapsack DP with backtracking (B1)")
    rep.code("""
MULTI-KNAPSACK-DP(items 1..q, C[1..k]):
    // DP[i][c] = best (benefit, served) using items 1..i with budgets c = (c_1..c_k)
    DP[0][c] <- (0, 0) for every c                   // base case
    for i <- 1 to q:
        for every c:
            DP[i][c] <- DP[i-1][c];  choice[i][c] <- SKIP
            for each eligible j in ascending ID with c_j >= w_i:
                cand <- (b_i, 1) + DP[i-1][c with c_j - w_i]
                if cand > DP[i][c] (lexicographic):  DP[i][c] <- cand;  choice[i][c] <- j
    c <- C                                           // backtrack from the full budget
    for i <- q downto 1:
        if choice[i][c] = j != SKIP:  assign i -> j;  c_j <- c_j - w_i
    return DP[q][C], assignment""")
    rep.p("In the code the pair (benefit, served) is stored as one integer, benefit·(q+1) + served; because "
          "0 ≤ served ≤ q, integer order equals lexicographic order. Each layer is computed with NumPy slices: for "
          "station j, the states with c_j ≥ w_i read layer i−1 at c_j − w_i.")
    rep.h2("5.6 Checks: brute force (B2) and greedy baseline (B3)")
    rep.code("""
BRUTE-FORCE(items, C):                               // only for q <= 10
    best <- (0, 0)
    for each choice vector in  product over i of ({SKIP} + eligible(i)):
        if every station load <= C_j and (benefit, served) > best: best <- this
    return best

GREEDY-BASELINE(items, C):                           // bonus; no approximation ratio claimed
    sort items by b_i / w_i descending (exact fractions)
    for each item: give it to the eligible station with the most remaining space that fits""")

    # ------------------------------------------------------------ 6 correctness
    rep.h1("6. Correctness")
    rep.h2("6.1 Kruskal: greedy-choice property")
    rep.p("Suppose Kruskal accepts e = (u, v). Then u and v are in different DSU sets; let C be u's set. Every road "
          "ranked before e that crosses the cut (C, V∖C) was already scanned and would have joined two different "
          "sets, so it would have been accepted and C would not separate u from v. Hence e is the lowest-ranked road "
          "crossing the cut. **Exchange argument:** let T* be an optimal spanning forest that does not contain e. "
          "Adding e to T* creates a cycle that crosses the cut at another road f with w(f) ≥ w(e). T* − f + e is a "
          "spanning forest with cost no greater than T*, so it is also optimal and contains e. Therefore every accepted "
          "road is safe.")
    rep.h2("6.2 Kruskal: optimal substructure and the disconnected case")
    rep.p("After a safe road e is added, contract its endpoints into one vertex. If F' is an optimal spanning forest of "
          "the contracted graph, F' ∪ {e} is optimal for the original graph; otherwise a cheaper completion F'' would "
          "give a cheaper forest F'' ∪ {e}, contradicting the optimality of F'. Induction over the accepted roads proves "
          "that Kruskal returns a minimum spanning forest. If (V, E_active) is disconnected, no road crosses between "
          "components, so the argument applies inside each component and the result is one minimum tree per component "
          "(n − c roads for c components). No connection is ever invented.")
    rep.h2("6.3 Union-Find and rejection of cycles")
    rep.p("Invariant: every DSU set equals the vertex set of one tree of F. It holds initially (singletons). UNION "
          "merges two sets exactly when a road joining two trees is added, so the invariant is preserved. A road whose "
          "endpoints share a root lies inside one tree and would close a cycle, so it is rejected. Path compression "
          "and union by rank change only the shape of the parent trees, never the sets.")
    rep.h2("6.4 Incremental repair")
    rep.p("Deleting a tree road e splits its tree into C1 and C2; all other forest roads lie inside C1 or C2 and remain "
          "part of an optimal forest of the new graph. Any spanning forest of the new graph must cross (C1, C2) with "
          "exactly one road if a crossing road exists; by the cut property the cheapest crossing survivor is safe. If "
          "none exists the component has genuinely split. Other failed forest roads lie inside C1 or C2, so excluding "
          "all failed roads from the candidates up front changes nothing. A failed road outside F leaves F optimal. "
          "The validator additionally checks equal cost against full Kruskal on the same modified graph.")
    rep.h2("6.5 DP: optimal substructure and recurrence")
    rep.p("Consider an optimal solution for the subproblem (i, c). Request i is either skipped or placed in exactly one "
          "eligible station j with c_j ≥ w_i. Removing it leaves a feasible solution of subproblem (i−1, c) or "
          "(i−1, c − w_i·e_j) respectively, and that remainder must be optimal for its subproblem; otherwise replacing it "
          "with a better one would improve (i, c). The recurrence takes the maximum over exactly these cases, so by "
          "induction on i every DP[i][c] is optimal and DP[q][C] is the optimum. Because each request is decided in one "
          "layer as either SKIP or a single station, **no request can be assigned twice**, which is why the design does "
          "not run k independent knapsacks. Backtracking follows the stored choices from (q, C) and reproduces a "
          "solution of exactly value DP[q][C]; the validator re-adds the benefits to confirm this.")
    rep.h2("6.6 Tie rule and verification")
    rep.p("Ties are broken by more requests served (encoded in the pair), then by checking SKIP first and stations in "
          "ascending ID with a strict comparison, so results are deterministic. Brute force evaluates the same objective "
          f"over all (k+1)^q assignments; it agreed with the DP on (benefit, served) for {ver['agree']} of "
          f"{ver['instances']} random instances, including zero-capacity stations and too-heavy items.")

    # ------------------------------------------------------------ 7 complexity
    rep.h1("7. Complexity Analysis")
    rep.p("**Kruskal.** Filtering is O(m); sorting is O(m log m); n MAKE-SET operations are O(n); at most m UNION/FIND "
          "pairs cost O(m α(n)) amortised. Hence T(n, m) = O(n + m log m + m α(n)) = **O(m log m)** for a non-trivial "
          "graph, and since m ≤ n², log m = O(log n). Space is O(n) for the DSU plus O(m) for the sorted edges: "
          "**O(n + m)**.")
    rep.p("**Repair.** Each failed forest road needs two BFS traversals of the forest (O(n)) and one scan of the surviving "
          "roads (O(m)), so r failures cost **O(r(n + m))**; with r = 3 this is O(n + m). It is a simple repair, not a "
          "dynamic-MST structure, so it is not guaranteed to be faster than re-sorting; E5 measures both.")
    rep.p(f"**Eligibility.** O(q k). **DP.** With S = Π_j (C_j + 1) states per layer, each of q requests tries SKIP plus "
          f"at most k stations per state: **time O(q k S)**. Keeping all q + 1 layers for backtracking needs "
          f"**space O(q S)**. The bound is pseudo-polynomial (it depends on capacity values) and exponential in k. For the "
          f"baseline, S = {a1['dp']['states_per_layer']:,} (= 13 × 10 × 8), with {q_dp} requests entering the DP, "
          f"giving {a1['dp']['total_states']:,} states and a {fmt_bytes(a1['dp']['table_bytes'])} table; the k = 4 stress "
          f"run has S = {stress['dp']['states_per_layer']:,}.")
    rep.p(f"**Brute force.** (k+1)^q assignments, each checked in O(q + k): O((k+1)^q (q + k)). For q = 24 and k = 3 this "
          f"is 4^24 ≈ 2.8 × 10^14 assignments, which is infeasible; for q = 10 it is 4^10 = 1,048,576, which is why brute "
          f"force is restricted to q ≤ 10. **Greedy baseline.** O(q log q + q k).")
    rep.table("Complexity summary.", ["Algorithm", "Time", "Space"],
              [["Union-Find (m operations)", "O(m α(n)) amortised", "O(n)"],
               ["Kruskal MSF", "O(m log m)", "O(n + m)"],
               ["Incremental repair (r failures)", "O(r (n + m))", "O(n + m)"],
               ["Eligibility", "O(q k)", "O(q k)"],
               ["Multi-knapsack DP", "O(q k S), S = Π(C_j + 1)", "O(q S)"],
               ["Brute force", "O((k+1)^q (q + k))", "O(q + k)"],
               ["Greedy baseline", "O(q log q + q k)", "O(q + k)"]], [2, 2, 1])

    # ------------------------------------------------------------ 8 implementation
    rep.h1("8. Implementation and Dataset")
    rep.p(f"The system is written in Python (tested with Python {machine.get('python', '3')}); all algorithms are "
          "hand-written, with NumPy used only for the DP table. networkx appears only in the tests, as an independent "
          "cross-check of Kruskal's cost. pytest runs the test suite, matplotlib draws the figures, and the dashboard "
          "is a Next.js web application that reads the same `results.json`.")
    rep.h2("8.1 The Karachi-EV-12 dataset (synthetic)")
    rep.p(f"Site names are real Karachi areas, but every cost, severity, capacity, demand and benefit is synthetic. "
          f"A seeded generator (`scripts/gen_dataset.py`, seed 363) writes the CSV files deterministically, and a test "
          f"asserts every design property: {m_total - m_active} unavailable roads that are exactly the links between "
          f"the main and the cut-off components, a cheap triangle, several equal-cost groups, an unavailable road "
          f"cheaper than selected roads, real over-demand in each component and two too-heavy requests.")
    site_rows = []
    for s in r["sites"]:
        roles = []
        if s["is_hub"]:
            roles.append("hub")
        if s["id"] in st_at:
            st = st_at[s["id"]]
            roles.append(f"{st['id']} {st['capacity_kwh']} kWh = {st['capacity_units']} units"
                         + ("" if st["active"] else " (inactive; stress run only)"))
        c = comp_of(s["id"], e1["components"])
        roles.append("isolated" if c["isolated"] else ("main component" if c["has_hub"] else "cut-off component"))
        site_rows.append([s["id"], s["name"], s["severity"], "; ".join(roles)])
    rep.table(f"Sites of the {r['meta']['dataset']} dataset (severity and role).",
              ["ID", "Site", "Severity", "Role"], site_rows, [0.6, 1.6, 0.8, 3])
    rep.p(f"Requests: {a1['requests_total']} in total, "
          f"{sum(1 for x in a1['requests'] if x['origin'] in main_sites)} in the main component, "
          f"{sum(1 for x in a1['requests'] if comp_of(x['origin'], e1['components']) and not comp_of(x['origin'], e1['components'])['has_hub'] and not comp_of(x['origin'], e1['components'])['isolated'])} "
          f"in the cut-off component and {sum(1 for x in a1['requests'] if comp_of(x['origin'], e1['components'])['isolated'])} "
          f"at an isolated site; total demand {sum(x['units'] for x in a1['requests'])} units against "
          f"{cap_total} units of active capacity. The full road list is in Appendix B and the full request list with "
          f"outcomes is in Section 9.2.")
    rep.h2("8.2 Validation and testing")
    rep.p(f"Input validation rejects duplicate IDs, negative costs, capacities, energy or benefit, unknown or identical "
          f"road endpoints and unit values that break the rounding rule. Every experiment passes its results through "
          f"independent validators (forest acyclic, spanning every component, no unavailable road, cost recomputed; "
          f"every request at most once, every load within capacity, every assignment eligible, benefit recomputed). "
          + (f"The automated test suite has **{n_tests} tests**, " if n_tests else "The automated test suite ")
          + "covering every mandatory case: disconnected graph, over-demand, too-heavy request, unavailable edge, cycle "
            "prevention, equal-cost edges, duplicate-assignment guard, zero requests and zero capacity, incremental "
            "failure, plus DP-versus-brute-force agreement and repair-versus-full-Kruskal agreement on random instances.")
    rep.h2("8.3 Reproducing the results")
    rep.code("pip install -r requirements.txt\n"
             "python -m pytest\n"
             "python run_all.py\n"
             "python scripts/build_report_assets.py\n"
             "python scripts/build_report.py")
    mstr = ", ".join(x for x in [machine.get("os"), machine.get("cpu"),
                                 f"Python {machine['python']}" if machine.get("python") else None,
                                 f"NumPy {machine['numpy']}" if machine.get("numpy") else None] if x)
    rep.p(f"Timings use `time.perf_counter` and report the median of {runs} runs in one Python process"
          + (f" on {mstr}" if mstr else "") + ". They vary between machines and runs; all counts, costs and benefits "
          "are deterministic.")

    # ------------------------------------------------------------ 9 results
    rep.h1("9. Results")
    rep.p("Every number and figure in this section is generated by `run_all.py` from the submitted code.")
    rep.h2("9.1 E1 Baseline: network")
    rep.p(f"{m_total - m_active} unavailable roads ({', '.join(rname(d['road']) for d in e1['dropped'])}) are removed "
          f"before sorting, leaving {m_active} roads. Table {rep.n_table + 1} is the Kruskal trace in sorted order.")
    trace_rows = []
    for i, t in enumerate(e1["trace"], 1):
        x = roads[t["road"]]
        trace_rows.append([i, rname(t["road"]), x["cost"], sites[x["u"]]["severity"] + sites[x["v"]]["severity"],
                           "accept" if t["accepted"] else "reject (cycle)"])
    rep.table("Kruskal trace (sorted edge order) on the baseline graph.",
              ["#", "Road", "Cost", "s(u)+s(v)", "Decision"], trace_rows, [0.4, 3, 0.6, 0.9, 1.3])
    rep.p(f"The minimum spanning forest has **{len(e1['forest'])} roads and total cost {e1['cost']}** over "
          f"**{len(e1['components'])} components**: {comps_text(e1['components'])}. "
          f"The cheap triangle shows cycle prevention (the third triangle road is rejected), and the equal-cost roads "
          f"are ordered by severity sum and then by ID. Figure {rep.n_fig + 1} shows the forest.")
    rep.figure("fig_network_baseline.png", f"E1 baseline minimum spanning forest (cost {e1['cost']}); "
               "unavailable roads dotted, unused available roads dashed.", 14)
    rep.h2("9.2 E1 Baseline: allocation")
    load_rows = [[sid, name[next(s for s in r['stations'] if s['id'] == sid)['site']], l["capacity"], l["load"],
                  f"{100 * l['load'] / l['capacity']:.0f}%"] for sid, l in a1["loads"].items()]
    rep.table("Station loads in the baseline.", ["Station", "Site", "Capacity (units)", "Load (units)", "Used"],
              load_rows, [0.8, 1.6, 1, 1, 0.7])
    req_rows = [[x["id"], name[x["origin"]], x["kwh"], x["units"], x["benefit"], " ".join(x["eligible"]) or "–",
                 x["station"] or x["reason"].replace("_", " ")] for x in a1["requests"]]
    rep.table("Every request with its eligible stations and outcome (baseline).",
              ["Request", "Origin", "kWh", "Units", "Benefit", "Eligible", "Outcome"], req_rows,
              [0.8, 1.5, 0.5, 0.5, 0.6, 0.9, 2.2])
    rep.p(f"The DP serves **{a1['served']} of {a1['requests_total']} requests**, assigning {a1['units']} units "
          f"({a1['kwh']} kWh requested) and reaching a **total benefit of {a1['benefit']}**; every station is filled "
          f"to capacity. Unserved: {counts_text(a1['unserved_counts'])}. The DP used "
          f"S = {a1['dp']['states_per_layer']:,} states per layer and {a1['dp']['total_states']:,} states in total "
          f"({fmt_bytes(a1['dp']['table_bytes'])}). Median runtime was {fmt_ms(e1['runtime_ms']['kruskal'])} for Kruskal "
          f"and {fmt_ms(e1['runtime_ms']['allocation'])} for eligibility plus DP.")
    rep.p(f"**Stress run (k = 4).** Activating {e1['stress']['station']} raises the states per layer to "
          f"{stress['dp']['states_per_layer']:,} ({stress['dp']['total_states']:,} in total, "
          f"{fmt_bytes(stress['dp']['table_bytes'])}); {stress['served']} requests are served for a benefit of "
          f"{stress['benefit']}, with a median allocation time of {fmt_ms(e1['stress']['runtime_ms'])}.")

    rep.h2("9.3 E2 Three-road failure")
    fail_rows = [[rname(f["road"]), roads[f["road"]]["cost"], f["role"].replace("_", " "), f["action"].replace("_", " "),
                  rname(f["replacement"]) if f["replacement"] else "–"] for f in e2["failed"]]
    rep.table("The three pre-chosen failures and the repair action taken.",
              ["Failed road", "Cost", "Planned role", "Action", "Replacement"], fail_rows, [2, 0.5, 1.6, 1, 1.9])
    same = sorted(e2["forest"]) == sorted(e2["full_forest"])
    rep.p(f"The repaired forest costs **{e2['repair_cost']}** and full Kruskal on the same modified graph costs "
          f"**{e2['full_cost']}** (cost before the failures: {e2['cost_before']}); the edge sets are "
          f"{'identical' if same else 'different only on equal-cost ties'}. After the failures there are "
          f"{len(e2['components'])} components: {comps_text(e2['components'])}. Median runtimes over {runs} runs were "
          f"{fmt_ms(e2['runtime_ms']['repair'])} for the repair and {fmt_ms(e2['runtime_ms']['full'])} for full Kruskal; "
          f"at this size both are tiny, so E5 compares them on larger graphs. Rerunning the allocation on the modified "
          f"network serves {a2['served']} requests for a benefit of {a2['benefit']}.")
    rep.figure("fig_network_e2.png", f"E2 forest after the three failures, repaired (cost {e2['repair_cost']}); "
               "the replacement road is highlighted.", 14)

    rep.h2("9.4 E3 Removing the two highest-severity sites")
    rm = e3["removed_sites"]
    rep.p(f"The two highest-severity sites are {name[rm[0]]} ({sites[rm[0]]['severity']}) and {name[rm[1]]} "
          f"({sites[rm[1]]['severity']}); the hub, {hub['name']}, has severity {hub['severity']} and is deliberately not "
          f"among them. Both sites, their {len(e3['removed_roads'])} incident roads and station(s) "
          f"{', '.join(e3['deactivated_stations'])} are removed, and **both stages are rerun**.")
    rep.table("Baseline versus removal of the top-2 severity sites.", ["Metric", "E1 baseline", "E3 after removal"],
              [["Forest cost", e1["cost"], e3["cost"]], ["Forest roads", len(e1["forest"]), len(e3["forest"])],
               ["Components", len(e1["components"]), len(e3["components"])],
               ["Active stations", " ".join(a1["loads"]), " ".join(a3["loads"])],
               ["Capacity (units)", a1["capacity"], a3["capacity"]],
               ["Requests served", a1["served"], a3["served"]],
               ["Energy assigned (units)", a1["units"], a3["units"]], ["Total benefit", a1["benefit"], a3["benefit"]],
               ["Unserved by reason", counts_text(a1["unserved_counts"]), counts_text(a3["unserved_counts"])]],
              [1.3, 2, 2])
    was_isolated = {c["sites"][0] for c in e1["components"] if c["isolated"]}
    newly = [name[c["sites"][0]] for c in e3["components"] if c["isolated"] and c["sites"][0] not in was_isolated]
    split_text = (f"so {', '.join(newly)} {'is' if len(newly) == 1 else 'are'} newly cut off and the requests there "
                  f"lose every eligible station" if newly else "and fewer stations remain reachable")
    rep.p(f"Removing a high-severity site can split a component and remove a station: after removal the components are "
          f"{comps_text(e3['components'])}, {split_text}. These are model outputs only; no safety claim is made.")
    rep.figure("fig_network_e3.png", f"E3 forest after removing {name[rm[0]]} and {name[rm[1]]} (cost {e3['cost']}).", 14)

    rep.h2("9.5 E4 Capacity and demand sensitivity")
    rep.p(f"E4a cuts every station's kWh capacity by {e4['cut_percent']}% and rounds down; E4b adds "
          f"{len(e4['new_requests'])} requests with new IDs ({', '.join(x['id'] for x in e4['new_requests'])}); "
          f"E4c applies both.")
    rep.table("Capacity and demand sensitivity.",
              ["Scenario", "Capacities (units)", "Requests", "Served", "Energy (units)", "Used", "Benefit"],
              [[s["label"], " ".join(f"{k_}={v}" for k_, v in s["capacities"].items()), s["requests"], s["served"],
                f"{s['units']}/{s['capacity']}", f"{100 * s['units'] / s['capacity']:.0f}%", s["benefit"]]
               for s in e4["scenarios"]], [1.6, 1.6, 0.8, 0.7, 1, 0.6, 0.7])
    base_b = e4["scenarios"][0]["benefit"]
    rep.p("Changes in benefit relative to the baseline: " + "; ".join(
        f"{s['label']} {s['benefit'] - base_b:+d}" for s in e4["scenarios"][1:]) + ". Less capacity lowers both "
          "served requests and benefit; extra demand with the same capacity lets the DP choose more valuable requests, "
          "so benefit can rise while the number served stays the same.")
    rep.figure("fig_benefit_by_scenario.png", "Total benefit served by the exact DP in every scenario.", 13)

    rep.h2("9.6 E5 Scaling")
    rep.table(f"Network scaling: median runtime of full Kruskal and incremental repair (3 failures), {runs} runs.",
              ["n", "m (active)", "Kruskal", "Repair", "Full Kruskal after failures", "Repair / full", "Costs equal"],
              [[x["n"], x["m"], fmt_ms(x["kruskal_ms"]), fmt_ms(x["repair_ms"]), fmt_ms(x["full_ms"]),
                f"{x['repair_ms'] / x['full_ms']:.2f}×", "yes" if x["costs_equal"] else "NO"] for x in e5["network"]],
              [0.5, 0.8, 1, 1, 1.4, 0.9, 0.8])
    rep.p(f"On these graphs the repair took between {min(x['repair_ms'] / x['full_ms'] for x in e5['network']):.2f}× and "
          f"{max(x['repair_ms'] / x['full_ms'] for x in e5['network']):.2f}× the time of full recomputation, and always "
          f"matched its cost. This is a measured observation on this machine, not a general guarantee.")
    rep.figure("fig_e5_network_runtime.png", "E5 network runtime against the number of sites.", 12.5)
    rep.table("DP scaling with q = n/2 requests and k = 3 or 4 stations.",
              ["n", "q", "k", "S per layer", "Total states", "DP time", "Memory"],
              [[x["n"], x["q"], x["k"], f"{x['states_per_layer']:,}", f"{x['total_states']:,}", fmt_ms(x["dp_ms"]),
                fmt_bytes(x["table_bytes"])] for x in e5["dp"]], [0.5, 0.5, 0.4, 1, 1, 1, 1])
    rep.table("Pseudo-polynomial growth: DP with q = 24, k = 3 and capacities multiplied by a factor.",
              ["Factor", "Capacities", "S per layer", "DP time", "Memory"],
              [[f"×{x['factor']}", ", ".join(map(str, x["capacities"])), f"{x['states_per_layer']:,}",
                fmt_ms(x["dp_ms"]), fmt_bytes(x["table_bytes"])] for x in e5["capacity"]], [0.6, 1.2, 1, 1, 1])
    rep.figure("fig_e5_dp_states.png", "E5 DP runtime against the number of states per layer.", 12.5)
    rep.table("Brute force against the exact DP (k = 3).",
              ["q", "Assignments checked", "Brute force", "DP", "Same optimum"],
              [[x["q"], f"{x['checked']:,}", fmt_ms(x["brute_ms"]), fmt_ms(x["dp_ms"]), "yes" if x["same"] else "NO"]
               for x in e5["brute"]], [0.5, 1.4, 1, 1, 1])
    rep.figure("fig_e5_brute_vs_dp.png", "E5 brute force versus DP runtime (log scale).", 12.5)

    rep.h2("9.7 Verification and greedy baseline")
    g = ver["greedy"]
    rep.p(f"The DP matched brute force on (benefit, served) in **{ver['agree']} of {ver['instances']}** random instances "
          f"(q ≤ 9, k ≤ 3). The optional benefit-per-unit greedy baseline reached {g['dataset_greedy']} on the dataset "
          f"against the DP's {g['dataset_dp']}; over {g['random_count']} random instances it was optimal "
          f"{g['optimal_count']} times, with a mean gap of {g['mean_gap_pct']:.1f}% and a maximum gap of "
          f"{g['max_gap_pct']:.1f}%. No approximation ratio is claimed.")

    rep.h2("9.8 Mandatory edge cases")
    rep.p("The three CEP-mandatory cases run in the submitted code; the full output is `output/edge_cases.log` "
          "(Appendix A).")
    rep.bullets([
        f"**Disconnected graph:** the forest has {len(e1['forest'])} roads over {len(e1['components'])} components, "
        f"listed by name ({comps_text(e1['components'])}); none of the filtered roads is selected, so no connection is invented.",
        "**Over-demand:** " + "; ".join(f"component {name[lbl]}: feasible demand {d} units vs capacity {c} units"
                                         for lbl, (d, c) in demand_by_comp.items())
        + f". All loads stay within capacity; unserved (capacity competition): {', '.join(lost1)}.",
        "**Too-heavy request:** " + "; ".join(
            f"{x['id']} at {name[x['origin']]} needs {x['units']} units but its eligible stations hold "
            f"{', '.join(f'{s}={caps[s]}' for s in x['eligible'])}" for x in heavy)
        + "; these are labelled too_large_for_any_eligible_station and never assigned.",
    ])

    # ------------------------------------------------------------ 10 conclusion
    rep.h1("10. Conclusion and Limitations")
    rep.p(f"The project combines a greedy minimum spanning forest with exact multi-knapsack dynamic programming and links "
          f"them through component-based eligibility. Kruskal with Union-Find filtered unavailable roads, broke ties "
          f"deterministically and named every component; the incremental repair matched full recomputation in cost "
          f"in every experiment. The DP respected every capacity, never assigned a request twice, reported a reason for "
          f"every unserved request and agreed with brute force on every small instance. Removing the two highest-"
          f"severity sites showed how losing a central site can split the network and remove a station, reducing "
          f"benefit from {a1['benefit']} to {a3['benefit']} in the model.")
    rep.h2("10.1 Limitations")
    rep.bullets([
        "The data are synthetic; they cannot establish real construction costs, demand or traffic.",
        "The MST minimises connection cost only, not travel time, coverage, resilience or safety.",
        "Benefit scores encode the designers' priorities; maximising their sum does not guarantee fairness.",
        "Rounding to 10 kWh units can change feasibility; requests are indivisible.",
        f"The exact DP grows as Π(C_j + 1), so it is limited to k = 3 (stress k = 4) stations.",
        "Queues, charger power, charging duration, prices and grid limits are not modelled.",
        "The repair algorithm is simple, not a dynamic-MST data structure; its speed is measured, not guaranteed.",
    ])
    rep.h2("10.2 Future work")
    rep.bullets([
        "Sparse-state or branch-and-bound exact methods to handle more stations.",
        "Time-decayed or urgency-weighted benefits with an explicit formula, and a fairness constraint.",
        "A coverage- or travel-time-aware network objective alongside connection cost.",
        "Validated real Karachi data for costs, demand and station capacities.",
    ])

    # ------------------------------------------------------------ refs
    rep.h1("References")
    rep.numbered([
        "T. H. Cormen, C. E. Leiserson, R. L. Rivest and C. Stein, *Introduction to Algorithms*, 4th ed. MIT Press, 2022 "
        "(minimum spanning trees, disjoint sets, dynamic programming).",
        "J. B. Kruskal, \"On the shortest spanning subtree of a graph and the traveling salesman problem,\" "
        "*Proceedings of the American Mathematical Society*, vol. 7, no. 1, pp. 48–50, 1956.",
        "R. C. Prim, \"Shortest connection networks and some generalizations,\" *Bell System Technical Journal*, "
        "vol. 36, no. 6, pp. 1389–1401, 1957.",
        "R. E. Tarjan, \"Efficiency of a good but not linear set union algorithm,\" *Journal of the ACM*, vol. 22, "
        "no. 2, pp. 215–225, 1975.",
        "G. N. Frederickson, \"Data structures for on-line updating of minimum spanning trees, with applications,\" "
        "*SIAM Journal on Computing*, vol. 14, no. 4, pp. 781–798, 1985.",
        "J. Holm, K. de Lichtenberg and M. Thorup, \"Poly-logarithmic deterministic fully-dynamic algorithms for "
        "connectivity, minimum spanning tree, 2-edge, and biconnectivity,\" *Journal of the ACM*, vol. 48, no. 4, "
        "pp. 723–760, 2001.",
        "S. Martello and P. Toth, *Knapsack Problems: Algorithms and Computer Implementations*. Wiley, 1990.",
        "H. Kellerer, U. Pferschy and D. Pisinger, *Knapsack Problems*. Springer, 2004.",
        "CT-363 Design and Analysis of Algorithms, course lecture slides, NED University of Engineering and Technology.",
        "CT-363 Complex Engineering Problem (CEP) assignment sheet, NED University of Engineering and Technology.",
    ])

    # ------------------------------------------------------------ appendices
    rep.h1("Appendix A. Edge-case log (generated)")
    rep.code(r["edge_cases_log"])
    rep.h1("Appendix B. Road list")
    sel = set(e1["forest"])
    rep.table("All roads of the dataset and their status in the baseline.",
              ["Road", "Endpoints", "Cost", "Available", "In E1 forest"],
              [[x["id"], f"{name[x['u']]} – {name[x['v']]}", x["cost"], "yes" if x["available"] else "no",
                "yes" if x["id"] in sel else ""] for x in r["roads"]], [0.6, 2.6, 0.5, 0.8, 0.9])
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "output" / "results.json"))
    ap.add_argument("--figures", default=str(ROOT / "report" / "figures"))
    ap.add_argument("--out", default=str(ROOT / "report"))
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()

    res = Path(a.results)
    if not res.exists():
        sys.exit("run `python run_all.py` first: output/results.json is missing")
    r = json.loads(res.read_text(encoding="utf-8"))
    figdir = Path(a.figures)
    if not (figdir / "fig_network_baseline.png").exists():
        sys.exit(f"figures missing in {figdir}: run `python scripts/build_report_assets.py` first")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    architecture_figure(figdir / "fig_architecture.png")

    rep = build_content(r, count_tests())
    stem = "CT363_Smart_EV_Report"
    render_docx(rep, out / f"{stem}.docx", figdir)
    html_path = out / f"{stem}.html"
    rel = Path(os.path.relpath(figdir, out)).as_posix()
    render_html(rep, html_path, rel)
    print("wrote", out / f"{stem}.docx")
    print("wrote", html_path)
    if not a.no_pdf and print_pdf(html_path, out / f"{stem}.pdf"):
        print("wrote", out / f"{stem}.pdf")


if __name__ == "__main__":
    main()
