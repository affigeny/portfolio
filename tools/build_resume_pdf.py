#!/usr/bin/env python3
"""Печатает резюме в PDF — ровно одна страница A4 на роль.

Зачем отдельный скрипт
----------------------
Резюме — одностраничник. Это не пожелание, а требование к жанру:
рекрутер открывает вложение, видит вторую страницу с двумя строчками
«Опыт (продолжение)» — и закрывает. Соблюдать это руками нельзя:
правил в `@media print` много, контент меняется, и проверять «а не
расползлось ли» надо каждый раз.

Поэтому скрипт делает две вещи:
  1. печатает каждое резюме в PDF через headless-Chrome;
  2. считает страницы и падает, если хоть одно резюме не влезло
     в одну страницу.

Второе важнее первого. Печать без проверки — это обещание без
реализации: PDF соберётся, но окажется двухстраничным, и узнают об
этом не здесь, а когда файл уже ушёл работодателю.

Запуск
------
    python3 tools/build_resume_pdf.py                  # все резюме
    python3 tools/build_resume_pdf.py resumes/resume_cx.html
    python3 tools/build_resume_pdf.py --allow-overflow  # не падать

Результат — в `resumes/pdf/`. Возвращает 1, если что-то не влезло.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "resumes"
OUT = SRC / "pdf"

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Сколько миллисекунд виртуального времени дать странице на отрисовку
# до печати. Резюме статические, но шрифты и вёрстка должны успеть
# посчитаться, иначе Chrome напечатает сырую раскладку.
VIRTUAL_TIME_BUDGET = 8000


def find_chrome() -> str:
    if Path(CHROME).exists():
        return CHROME
    for name in ("google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    sys.exit(
        "Не нашёл Chrome. Скрипт печатает им: нужен "
        "/Applications/Google Chrome.app или chromium в PATH."
    )


def print_to_pdf(chrome: str, page: Path, dst: Path) -> None:
    """Один проход headless-Chrome: страница -> PDF.

    `--no-pdf-header-footer` убирает служебную строку с датой и
    адресом, которую Chrome иначе впечатывает вниз каждой страницы.
    """
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--virtual-time-budget={VIRTUAL_TIME_BUDGET}",
        f"--print-to-pdf={dst}",
        page.as_uri(),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 or not dst.exists():
        sys.exit(
            f"Chrome не смог напечатать {page.name}:\n"
            f"{proc.stderr.strip()[:800]}"
        )


def page_count(pdf: Path) -> int:
    """Считает страницы. pypdf — единственная зависимость, и только
    для этого: обойтись без неё можно разве что grep'ом по
    `/Type /Page`, а он врёт на сжатых объектных потоках."""
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit(
            "Нужен pypdf: pip install pypdf\n"
            "Без него количество страниц не посчитать, а это и есть "
            "главная проверка скрипта."
        )
    return len(PdfReader(str(pdf)).pages)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pages", nargs="*",
                    help="конкретные резюме; по умолчанию все из resumes/")
    ap.add_argument("--allow-overflow", action="store_true",
                    help="не падать, если резюме не влезло в страницу")
    args = ap.parse_args(argv[1:])

    if args.pages:
        pages = [Path(p).resolve() for p in args.pages]
    else:
        pages = sorted(SRC.glob("*.html"))
    if not pages:
        print(f"В {SRC} не нашёл ни одного *.html")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()

    results: list[tuple[str, int, Path]] = []
    for page in pages:
        dst = OUT / f"{page.stem}.pdf"
        print_to_pdf(chrome, page, dst)
        results.append((page.stem, page_count(dst), dst))

    width = max(len(name) for name, _, _ in results)
    overflow: list[str] = []
    print()
    for name, count, dst in results:
        mark = "✓" if count == 1 else "✗"
        print(f"  {mark} {name:<{width}}  {count} стр.  "
              f"{dst.relative_to(ROOT)}  "
              f"({dst.stat().st_size // 1024} КБ)")
        if count != 1:
            overflow.append(f"{name}: {count} страниц")

    if overflow:
        print("\n✗ Не влезли в одну страницу A4:")
        for line in overflow:
            print("   ", line)
        print("\n  Что править: смотреть `@media print` в HTML резюме — "
              "уменьшить body font-size, row-gap у .grid, "
              "padding-bottom у .job, margin-bottom у .sec.")
        if not args.allow_overflow:
            return 1
        return 0

    print(f"\n✓ Все {len(results)} резюме — ровно по одной странице A4.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
