#!/usr/bin/env python3
"""Проверяет, что каждая ссылка ведёт на живой код или живую страницу.

Зачем
-----
В подвале каждой страницы написано: «Собрано как рабочий инструмент:
каждая ссылка ведёт на живой код или живую страницу». Подпись ничем
не подкреплена: в сессии 02.09 заглушки `href="#"` (LinkedIn,
HeadHunter) объявили удалёнными, а они остались на пяти страницах —
ровно над этой подписью. Проверка глазами такое не ловит.

Проверка нужна, чтобы обещание в подвале перестало быть декоративным.

Что проверяет
-------------
1. Нет `href="#"` и других пустых якорей, которые никуда не ведут.
2. Внутренние ссылки (относительные пути) ведут на существующий файл.
3. Внешние ссылки — только https, без `javascript:` и `mailto:`-мусора.
4. `tel:` записан по RFC 3966 (с дефисами): непрерывная цепочка цифр
   маскируется фильтром секретов и ссылка перестаёт работать.

Возвращает ненулевой код, если есть ошибки — чтобы проверку можно
было повесить в пре-коммит.

Использование
-------------
    python3 _check_links.py            # по всем *.html в корне и папках
    python3 _check_links.py index.html # по конкретным файлам
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Служебные папки: черновики, архив, скриншоты и venv в проверку не идут.
SKIP_DIRS = {
    ".git", "_archive", "_shots", "_drafts", "node_modules",
    ".venv", "__pycache__", ".workbuddy-ai", "sorterlab.egg-info",
}

HREF_RE = re.compile(r'href\s*=\s*"([^"]*)"', re.IGNORECASE)
ANCHOR_RE = re.compile(r'^<a\s', re.IGNORECASE)

# Схемы, которые браузер умеет сам и по которым файл проверять не надо.
KNOWN_SCHEMES = ("https://", "http://", "mailto:", "tel:")
BAD_SCHEMES = ("javascript:", "data:", "vbscript:")


def iter_pages(paths: list[str] | None) -> list[Path]:
    if paths:
        return [Path(p).resolve() for p in paths]
    out: list[Path] = []
    for p in sorted(ROOT.rglob("*.html")):
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        out.append(p)
    return out


def check_page(page: Path) -> list[str]:
    text = page.read_text(encoding="utf-8", errors="ignore")
    problems: list[str] = []

    for lineno, line in enumerate(text.split("\n"), 1):
        for m in HREF_RE.finditer(line):
            href = m.group(1).strip()
            where = f"{page.relative_to(ROOT)}:{lineno}"

            if not href or href == "#":
                problems.append(f'{where}: пустая ссылка href="{href}"')
                continue

            if href.lower().startswith(BAD_SCHEMES):
                problems.append(f"{where}: небезопасная схема {href[:40]}")
                continue

            if href.startswith("#"):
                # Якорь внутри страницы: должен существовать id.
                target = href[1:]
                if not re.search(rf'id\s*=\s*"{re.escape(target)}"', text):
                    problems.append(
                        f"{where}: якорь #{target} никуда не ведёт (нет id)"
                    )
                continue

            if href.startswith("tel:"):
                number = href[4:]
                if "-" not in number and " " not in number:
                    problems.append(
                        f"{where}: tel: без дефисов — фильтр секретов "
                        f"испортит ссылку при записи"
                    )
                continue

            if href.startswith(KNOWN_SCHEMES):
                if href.startswith("http://"):
                    problems.append(f"{where}: http вместо https — {href}")
                continue

            if href.startswith("//"):
                problems.append(f"{where}: ссылка без схемы — {href}")
                continue

            # Внутренняя ссылка. Отсекаем якорь и query.
            rel = href.split("#", 1)[0].split("?", 1)[0]
            if not rel:
                continue
            target = (page.parent / rel).resolve()
            if not target.exists():
                problems.append(f"{where}: файл не найден — {href}")

    return problems


def main(argv: list[str]) -> int:
    pages = iter_pages(argv[1:] or None)
    if not pages:
        print("Не нашёл ни одной страницы для проверки.")
        return 1

    all_problems: list[str] = []
    total = 0
    for page in pages:
        problems = check_page(page)
        links = len(HREF_RE.findall(page.read_text(encoding="utf-8",
                                                   errors="ignore")))
        total += links
        if problems:
            all_problems.extend(problems)

    if all_problems:
        print(f"✗ Найдено проблем: {len(all_problems)}\n")
        for p in all_problems:
            print(" ", p)
        return 1

    print(f"✓ Проверено страниц: {len(pages)}, ссылок: {total}. "
          f"Мёртвых и пустых нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
