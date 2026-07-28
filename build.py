#!/usr/bin/env python3
"""
Mixin Field Manual — one-command book builder.

Assembles chapters/ into print-ready HTML with embedded book typography:

    python build.py            # build/MixinFieldManual.html  (full book)
                               # build/MixinFieldManual-Sample.html  (cover + Ch.1)
                               # build/MixinFieldManual.md  (combined source, for pandoc later)

PDF step (no toolchain needed): open the HTML in any browser -> Ctrl+P ->
"Save as PDF" -> enable "Background graphics", default margins. The stylesheet
carries @page rules, chapter page-breaks, and print-safe fonts, so the browser
render *is* the layout.

Requires: pip install markdown   (pure Python, no other dependencies)
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("Missing dependency: run  pip install markdown  and retry.")

ROOT = Path(__file__).resolve().parent
CHAPTERS_DIR = ROOT / "chapters"
BUILD_DIR = ROOT / "build"

EDITION = "First Edition (presale draft)"
VERSION = "0.9"
AUTHOR = "MrWizard94"
YEAR = datetime.date.today().year

CHAPTER_FILES = [
    "01-the-collision.md",
    "02-the-injection-toolbox.md",
    "03-reading-the-target.md",
    "04-when-two-mods-fix-the-same-bug.md",
    "05-wrapping-the-wrapper.md",
    "06-targeting-the-untargetable.md",
    "07-the-require-zero-doctrine.md",
    "08-ducks-accessors-invokers.md",
    "09-dev-lies-and-prod-truth.md",
    "10-debugging-applied-mixins.md",
    "11-probes-and-measured-claims.md",
    "12-shipping-it.md",
    "appendices.md",
]

TITLE_PAGE = f"""
<div class="titlepage">
  <p class="series">A field manual for people who ship</p>
  <h1 class="booktitle">The Mixin<br>Field Manual</h1>
  <p class="subtitle">Cross-mod compatibility for Forge &amp; NeoForge modders —<br>
  war stories, doctrine, and the discipline of patching code you don't own</p>
  <p class="author">{AUTHOR}</p>
  <p class="edition">{EDITION} &middot; v{VERSION} &middot; {YEAR}</p>
</div>
<div class="colophon">
  <p>Copyright &copy; {YEAR} {AUTHOR}. All rights reserved. Licensed for personal use;
  please don't redistribute — this book is how independent tool-building gets funded.</p>
  <p>Every code excerpt in this book is from shipped, working mods maintained by the
  author. Nothing here is theoretical.</p>
</div>
"""

SAMPLE_FRONT = f"""
<div class="titlepage">
  <p class="series">Free sample &mdash; Chapter 1 of 12</p>
  <h1 class="booktitle">The Mixin<br>Field Manual</h1>
  <p class="subtitle">Cross-mod compatibility for Forge &amp; NeoForge modders</p>
  <p class="author">{AUTHOR}</p>
  <p class="edition">{EDITION} &middot; {YEAR}</p>
</div>
<div class="colophon">
  <p>This sample chapter is free to share, unmodified. The full manual &mdash; twelve
  chapters and four appendices, every fix from shipped mods &mdash; is available on Gumroad.</p>
</div>
"""

SAMPLE_BACK = """
## What's in the full manual

You just read Chapter 1. The remaining eleven chapters and four appendices:

**Part I — Foundations:** the injection toolbox ranked by how well each tool coexists
with strangers (spoiler: `@Redirect` is the worst neighbor on the list) · reading any
target with `javap` and CFR — descriptors, mappings, durable injection points.

**Part II — War Stories, all shipped:** the full resolution playbook for colliding
patches (cancellers, config plugins, who yields and why) · composing your
`@WrapOperation` over another mod's — including a self-calibrating matrix trick that
measures the other mod's transform instead of guessing it · targeting synthetic Kotlin
lambdas and deliberately obfuscated internals, with the four-clause etiquette that
keeps version-pins from rotting · the `require = 0` doctrine — compat mods that never
crash a stranger's pack · ducks, accessors, invokers, and the ClassCastException that
taught the whole ecosystem a lesson.

**Part III — Production Discipline:** why mixins work in dev and die in production
(refmaps, annotation processors, SRG, jar-in-jar) · debugging applied mixins and
bisecting a 300-mod pack in O(log n) launches · the probe methodology — how measurement
killed a beautiful, wrong hypothesis and saved weeks · shipping: version policy, config
hygiene, and the release checklist.

**Appendices:** @At and descriptor cheat sheets · MixinExtras quick reference · the
printable Compat Checklist · javap/CFR recipes.

**Get the full manual:** [GUMROAD LINK] — early-bird pricing for presale buyers, free
updates to the first edition.
"""

BOOK_CSS = """
:root { --ink:#1a1d21; --muted:#5c6570; --rule:#d7dce1; --code-bg:#f4f6f8;
        --accent:#8a4b12; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: Georgia, 'Times New Roman', serif; color: var(--ink);
       line-height: 1.55; font-size: 11.5pt; margin: 0 auto; max-width: 7in;
       padding: 0 0.5in; background:#fff; }
@page { size: letter; margin: 0.9in 0.85in; }
@media print { body { max-width:none; padding:0; } }

.titlepage { text-align:center; padding-top:2.2in; page-break-after: always; }
.series { letter-spacing:.18em; text-transform:uppercase; font-size:9pt; color:var(--muted); }
.booktitle { font-size:34pt; line-height:1.1; margin:.4em 0 .3em; font-weight:700; }
.subtitle { font-size:12.5pt; color:var(--muted); font-style:italic; }
.author { margin-top:2.2em; font-size:13pt; letter-spacing:.06em; }
.edition { color:var(--muted); font-size:9.5pt; }
.colophon { page-break-after: always; padding-top:4.5in; font-size:9pt;
            color:var(--muted); }

.toc { page-break-after: always; }
.toc h1 { font-size:20pt; }
.toc ol { list-style:none; padding:0; }
.toc li { margin:.45em 0; font-size:11.5pt; }
.toc .part { margin-top:1.2em; font-weight:700; letter-spacing:.05em;
             text-transform:uppercase; font-size:9.5pt; color:var(--accent); }

section.chapter { page-break-before: always; }
section.chapter:first-of-type { page-break-before: avoid; }
h1 { font-size:21pt; line-height:1.15; margin:1.6em 0 .2em; }
h1 + h3, h1 + p em { color:var(--muted); }
h2 { font-size:13.5pt; margin-top:1.7em; border-bottom:1px solid var(--rule);
     padding-bottom:.15em; }
h3 { font-size:11.5pt; color:var(--muted); font-weight:600; margin-top:-0.2em; }
p { orphans:3; widows:3; }
hr { border:none; border-top:1px solid var(--rule); margin:2em auto; width:38%; }
blockquote { margin:1em 0; padding:.1em 1em; border-left:3px solid var(--accent);
             color:var(--muted); }
strong { color:#000; }

code { font-family: Consolas, 'Cascadia Code', Menlo, monospace; font-size:9.5pt;
       background:var(--code-bg); padding:.08em .3em; border-radius:3px; }
pre { background:var(--code-bg); border:1px solid var(--rule); border-radius:6px;
      padding:.8em 1em; overflow-x:auto; page-break-inside:avoid; line-height:1.45; }
pre code { background:none; padding:0; font-size:9pt; }

table { border-collapse:collapse; width:100%; margin:1.1em 0; font-size:10pt;
        page-break-inside:avoid; }
th { text-align:left; border-bottom:2px solid var(--ink); padding:.35em .5em;
     font-size:9pt; letter-spacing:.04em; text-transform:uppercase; }
td { border-bottom:1px solid var(--rule); padding:.4em .5em; vertical-align:top; }

ul, ol { padding-left:1.4em; }
li { margin:.25em 0; }
input[type=checkbox] { margin-right:.4em; }
"""

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists"]


def chapter_title(md_text: str) -> str:
    match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = match.group(1) if match else "Untitled"
    title = re.sub(r"^Chapter\s+\d+\s*[—-]\s*", "", title)
    return title.replace("—", "&mdash;")


def render(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=MD_EXTENSIONS)


def html_document(title: str, body: str) -> str:
    return (f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<title>{title}</title>\n<style>{BOOK_CSS}</style>\n</head>\n"
            f"<body>\n{body}\n</body>\n</html>\n")


def build_toc(titles: list[str]) -> str:
    parts = {0: "Part I &mdash; Foundations", 3: "Part II &mdash; War Stories",
             8: "Part III &mdash; Production Discipline", 12: "&nbsp;"}
    items = []
    for index, title in enumerate(titles):
        if index in parts:
            items.append(f'<li class="part">{parts[index]}</li>')
        label = "" if index == 12 else f"{index + 1}. "
        items.append(f"<li>{label}{title}</li>")
    return ('<div class="toc"><h1>Contents</h1><ol>' + "".join(items) + "</ol></div>")


def main() -> None:
    BUILD_DIR.mkdir(exist_ok=True)

    sources = []
    for name in CHAPTER_FILES:
        path = CHAPTERS_DIR / name
        if not path.exists():
            sys.exit(f"Missing chapter file: {path}")
        sources.append(path.read_text(encoding="utf-8"))

    titles = [chapter_title(source) for source in sources]

    # Full book -------------------------------------------------------------
    body = [TITLE_PAGE, build_toc(titles)]
    for source in sources:
        body.append(f'<section class="chapter">{render(source)}</section>')
    book_html = html_document("The Mixin Field Manual", "\n".join(body))
    (BUILD_DIR / "MixinFieldManual.html").write_text(book_html, encoding="utf-8")

    # Combined markdown (future pandoc path) ---------------------------------
    combined = "\n\n\\newpage\n\n".join(sources)
    (BUILD_DIR / "MixinFieldManual.md").write_text(combined, encoding="utf-8")

    # Free sample: cover + Chapter 1 + upsell outro ---------------------------
    sample_body = [SAMPLE_FRONT,
                   f'<section class="chapter">{render(sources[0])}</section>',
                   f'<section class="chapter">{render(SAMPLE_BACK)}</section>']
    sample_html = html_document("The Mixin Field Manual — Sample Chapter",
                                "\n".join(sample_body))
    (BUILD_DIR / "MixinFieldManual-Sample.html").write_text(sample_html, encoding="utf-8")

    words = sum(len(s.split()) for s in sources)
    print(f"Built {len(sources)} sections ({words:,} words) -> {BUILD_DIR}")
    print("  MixinFieldManual.html         (full book, print-ready)")
    print("  MixinFieldManual-Sample.html  (free sample: cover + Ch.1 + contents pitch)")
    print("  MixinFieldManual.md           (combined source for a future pandoc pass)")
    print("\nPDF: open the HTML in a browser -> Ctrl+P -> Save as PDF")
    print("     (enable 'Background graphics'; keep default margins).")


if __name__ == "__main__":
    main()
