#!/usr/bin/env python3
"""Снимает страницы в заданной теме headless-Chrome'ом.

Зачем так, а не `--screenshot` по исходному файлу: тему задаёт
assets/theme.js из localStorage, а он читается до первой отрисовки.
Если поставить `data-theme` скриптом в конце <body>, переключатель уже
отработал и страница остаётся в системной теме.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT = ROOT / "_shots"

INJECT = (
    '<script>try{localStorage.setItem("pf-theme","__THEME__");'
    'localStorage.setItem("pf-metal","__METAL__")}catch(e){};'
    'document.documentElement.setAttribute("data-theme","__THEME__");'
    'document.documentElement.setAttribute("data-metal","__METAL__");'
    "</script>"
)


def shot(page: str, theme: str, metal: str = "brass", width: int = 1440,
         height: int = 1000, full: bool = False) -> Path:
    src = (ROOT / page).read_text(encoding="utf-8")
    tag = INJECT.replace("__THEME__", theme).replace("__METAL__", metal)
    # В <head>, до theme.js: иначе переключатель перебьёт выставленное.
    src = src.replace("<head>", "<head>" + tag, 1)
    tmp = ROOT / f".__shot_{page}"
    tmp.write_text(src, encoding="utf-8")
    if not OUT.exists():
        OUT.mkdir()
    suffix = "-full" if full else ""
    dst = OUT / f"{Path(page).stem}-{theme}-{metal}{suffix}.png"
    args = [
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--disable-dev-shm-usage", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--virtual-time-budget=4000",
    ]
    if full:
        # `--screenshot` режет по window-size; для полной страницы
        # берём заведомо большую высоту и потом режем по фактическому
        # содержимому.
        args += [f"--window-size={width},5200", f"--screenshot={dst}",
                 f"file://{tmp}"]
    else:
        args += [f"--window-size={width},{height}",
                 f"--screenshot={dst}", f"file://{tmp}"]
    try:
        subprocess.run(args, check=True, capture_output=True, timeout=120)
    finally:
        tmp.unlink(missing_ok=True)
    return dst


if __name__ == "__main__":
    pages = sys.argv[1:] or ["index.html"]
    full = "--full" in pages
    pages = [p for p in pages if not p.startswith("--")]
    for p in pages:
        for theme in ("light", "dark"):
            print(shot(p, theme, full=full))
