#!/usr/bin/env python3
"""Показывает печатную версию страницы картинкой.

Зачем, а не «распечатать в PDF и посмотреть»
-------------------------------------------
PDF, который делает Chrome, не посмотреть без отдельной библиотеки:
ни pdftoppm, ни mutool, ни gs в системе нет, а PyMuPDF тянет за собой
установку. При этом дефект печати обычно виден с первого взгляда —
тёмная подложка, съехавшая колонка, обрезанная таблица, — и лежит он
не в PDF, а в CSS.

Поэтому берётся копия страницы, `@media print` подменяется на
`@media all`, и получившийся вид снимается обычным скриншотом.
На картинке ровно то, что уйдёт на бумагу: те же правила, те же
разрывы, тот же масштаб A4.

Запуск
------
    python3 _print_preview.py index.html
    python3 _print_preview.py index.html resumes/resume_cx.html
    python3 _print_preview.py index.html --width 900

Картинки — в _shots/print/, имя: <страница>-print.png.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT = ROOT / "_shots" / "print"

# A4 при 96 dpi: 210 × 297 мм. Высота взята с запасом — страница
# печати обычно длиннее одного экрана, и длинный хвост нужен, чтобы
# увидеть разрывы между блоками.
A4_WIDTH = 794
A4_HEIGHT = 1123


def build_preview(page: str, width: int = A4_WIDTH) -> Path:
    src = (ROOT / page).read_text(encoding="utf-8")

    # design.css подключается ссылкой — его содержимое тоже надо
    # подменить, иначе печатные правила из него не сработают.
    css_link = re.search(r'<link[^>]+href="([^"]*design\.css)"[^>]*>', src)
    if css_link:
        css = (ROOT / css_link.group(1)).read_text(encoding="utf-8")
        src = src[: css_link.start()] + "<style>" + css + "</style>" + src[css_link.end() :]

    # Сама подмена: print → all. Сколько блоков заменено — столько
    # печатных правил реально участвует в вёрстке.
    src, n = re.subn(r"@media\s+print\b", "@media all", src)

    # Переключатель темы читает localStorage до отрисовки и может
    # перебить выставленное; в печатном виде он скрыт, но на всякий
    # случай гасим его заранее.
    inject = (
        "<script>try{localStorage.setItem('pf-theme','light');"
        "localStorage.setItem('pf-metal','brass')}catch(e){};</script>"
    )
    src = src.replace("<head>", "<head>" + inject, 1)

    OUT.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / f".__print_{Path(page).name}"
    tmp.write_text(src, encoding="utf-8")
    dst = OUT / f"{Path(page).stem}-print.png"
    args = [
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--disable-dev-shm-usage", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--virtual-time-budget=5000",
        f"--window-size={width},{A4_HEIGHT * 3}",
        f"--screenshot={dst}", f"file://{tmp}",
    ]
    try:
        subprocess.run(args, check=True, capture_output=True, timeout=120)
    finally:
        tmp.unlink(missing_ok=True)
    print(f"{dst.name}  (подменено блоков @media print: {n})")
    return dst


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    width = A4_WIDTH
    if "--width" in sys.argv:
        width = int(sys.argv[sys.argv.index("--width") + 1])
    pages = args or ["index.html"]
    for p in pages:
        build_preview(p, width)
