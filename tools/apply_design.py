#!/usr/bin/env python3
"""Дизайн-система и плавающий кластер: палитра, шкала 1.618, тема, металл,
   стрелка «далее» к следующему кейсу, иконки контактов.

   Кластер — вертикальный стек в правом нижнем углу:
     [металл] [тема] ─── [далее →] ─── [TG] [✉] [GH] [☎]

   Раньше «далее» и контакты жили отдельной плашкой `<aside
   class="next-step">` в подвале: вертикальный столбик с двумя
   смысловыми блоками, и контакты дублировали футер. Скрипт
   `_add_next_step.py` раскатывал её на семь страниц. Теперь её
   функция переехала в плавающий кластер — слитно, гармонично,
   всегда видно. Скрипт заодно снимает старую плашку
   (`<!-- next-step-v1 -->…<!-- /next-step-v1 -->`), так что откат
   возможен повторным запуском старого `_add_next_step.py`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CSS_HREF = "assets/design.css"
JS_SRC = "assets/theme.js"

SKIP_PREFIX = ("proto_", "prototype_", "index_photo", "_")
SKIP_NAMES = {"OVERVIEW.html"}

LINK_TAG = f'<link rel="stylesheet" href="{CSS_HREF}">'
SCRIPT_TAG = f'<script src="{JS_SRC}"></script>'

# Цепочка кейсов по чтению: «далее» ведёт к следующей странице.
# Замыкает кольцо sorterlab-simulator → index: из интерактива
# возвращаемся к оглавлению.
NEXT = {
    "index.html":              ("value.html",                 "Ценности и направления"),
    "value.html":              ("ux.html",                    "UX-кейс: кабинет самозанятого"),
    "ux.html":                 ("qa.html",                    "QA-кейс"),
    "qa.html":                 ("viral.html",                 "Механика внимания"),
    "viral.html":              ("writing.html",               "Тексты, которые решают задачу"),
    "writing.html":            ("archetypes.html",            "Архетипы в UHNWI"),
    "archetypes.html":         ("models.html",                "AI-бенчмарк: 28 моделей"),
    "models.html":             ("sorterlab.html",             "SorterLab: кейс"),
    "sorterlab.html":          ("sorterlab-simulator.html",   "SorterLab: модель"),
    "sorterlab-simulator.html":("index.html",                 "Портфолио"),
}

# Канонические контакты. Тот же набор, что в футере. Порядок:
# сначала канал прямого отклика (Telegram), потом почта, GitHub, телефон.
CONTACTS = [
    (
        "https://t.me/eandreev",
        "Telegram",
        '<path d="M22 2 2 10l7 3 3 8 3-4 5 3Z"/><path d="M9 13l9-8"/>',
    ),
    (
        "mailto:eugene.v.andreev@gmail.com",
        "Почта",
        '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    ),
    (
        "https://github.com/andreevgeny",
        "GitHub",
        '<path d="M12 2a10 10 0 0 0-3.16 19.5c.5.1.68-.22.68-.48v-1.7'
        "c-2.78.6-3.37-1.34-3.37-1.34-.46-1.16-1.11-1.47-1.11-1.47-.9-.62.07-.6"
        ".07-.6 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.08"
        ".63-1.33-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25"
        "-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.6 9.6 0 0 1 5 0c1.91-1.3 2.75-1.02"
        " 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.35 4.68"
        "-4.58 4.93.36.31.68.92.68 1.85v2.75c0 .26.18.57.69.48A10 10 0 0 0 12 2Z\"/>",
    ),
    (
        "tel:+7-925-888-58-82",
        "Телефон",
        '<path d="M22 16.9v3a2 2 0 0 1-2.2 2A19.8 19.8 0 0 1 3.1 4.2 2 2 0 0 1 5 2h3'
        'a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.6a2 2 0 0 1-.5 2.1L8.9 9.6a16 16 0 0 0 5.5'
        ' 5.5l1.2-1.2a2 2 0 0 1 2.1-.5c.8.3 1.7.5 2.6.6a2 2 0 0 1 1.7 2Z"/>',
    ),
]

MARK_OPEN = "<!-- design-system-v1 -->"
MARK_CLOSE = "<!-- /design-system-v1 -->"
NEXT_STEP_RE = re.compile(
    r"[ \t]*<!-- next-step-v1 -->.*?<!-- /next-step-v1 -->\s*\n?", re.S
)


def build_cluster(page_name: str) -> str:
    """Собирает разметку плавающего кластера для конкретной страницы."""
    next_url, next_label = NEXT.get(page_name, (None, None))
    next_html = ""
    if next_url:
        next_html = (
            f'  <div class="switch-cluster__sep" aria-hidden="true"></div>\n'
            f'  <a class="switch-cluster__next" href="{next_url}" '
            f'data-fab-next="{next_url}" title="Далее: {next_label}" '
            f'aria-label="Следующая страница: {next_label}">'
            f'<svg viewBox="0 0 24 24" aria-hidden="true">'
            f'<path d="M5 12h14M13 5l7 7-7 7"/></svg></a>\n'
        )
    cx_items = "\n".join(
        f'  <a class="switch-cluster__cx" href="{url}" aria-label="{label}">'
        f'<svg viewBox="0 0 24 24" aria-hidden="true">{svg}</svg></a>'
        for url, label, svg in CONTACTS
    )
    return f"""{MARK_OPEN}
<div class="switch-cluster">
  <button class="metal-toggle" type="button" data-metal-toggle aria-label="Акцент: латунь">
    <span class="metal-toggle__icon" aria-hidden="true"></span><span data-metal-label>Латунь</span>
  </button>
  <button class="theme-toggle" type="button" data-theme-toggle aria-label="Тема: как в системе">
    <span class="theme-toggle__icon" aria-hidden="true"></span><span data-theme-label>Авто</span>
  </button>
{next_html}  <div class="switch-cluster__sep" aria-hidden="true"></div>
{cx_items}
</div>
{MARK_CLOSE}"""


BLOCK_RE = re.compile(
    r"[ \t]*" + re.escape(MARK_OPEN) + r".*?" + re.escape(MARK_CLOSE) + r"\n?",
    re.S,
)


def strip_previous(src: str) -> str:
    """Снимает ранее поставленные блоки, чтобы не копить дубли."""
    src = BLOCK_RE.sub("", src)
    src = NEXT_STEP_RE.sub("", src)
    src = re.sub(r"[ \t]*" + re.escape(LINK_TAG) + r"\n?", "", src)
    src = re.sub(r"[ \t]*" + re.escape(SCRIPT_TAG) + r"\n?", "", src)
    return src


def insert_after_last_style(src: str, chunk: str) -> tuple[str, bool]:
    """Подключает CSS после авторского <style>: design.css переопределяет
    `:root` по порядку, иначе выиграет страница и палитра не соберётся."""
    matches = list(re.finditer(r"</style\s*>", src, re.I))
    if not matches:
        return src, False
    return src[: matches[-1].end()] + "\n" + chunk + src[matches[-1].end() :], True


def apply(path: Path) -> str:
    src = path.read_text(encoding="utf-8")
    src = strip_previous(src)
    notes: list[str] = []

    src, ok = insert_after_last_style(src, LINK_TAG)
    if not ok:
        head = re.search(r"<head[^>]*>", src, re.I)
        if head:
            src = src[: head.end()] + "\n" + LINK_TAG + src[head.end() :]
            notes.append("нет <style>")
        else:
            return f"{path.name:26} пропуск: не нашёл ни <style>, ни <head>"
    else:
        notes.append("css")

    head_close = re.search(r"</head\s*>", src, re.I)
    if head_close:
        src = src[: head_close.start()] + SCRIPT_TAG + "\n" + src[head_close.start() :]
        notes.append("тема")

    body = re.search(r"<body[^>]*>", src, re.I)
    if not body:
        return f"{path.name:26} пропуск: не нашёл <body>"
    cluster = build_cluster(path.name)
    src = src[: body.end()] + "\n" + cluster + src[body.end() :]
    notes.append("кластер")

    html_tag = re.search(r"<html\b[^>]*>", src, re.I)
    if html_tag:
        tag = html_tag.group(0)
        added = []
        if "data-theme" not in tag.lower():
            tag = tag[:-1] + ' data-theme="system">'
            added.append("data-theme")
        if "data-metal" not in tag.lower():
            tag = tag[:-1] + ' data-metal="brass">'
            added.append("data-metal")
        if added:
            src = src[: html_tag.start()] + tag + src[html_tag.end() :]
            notes.append("+".join(added))

    path.write_text(src, encoding="utf-8")
    return f"{path.name:26} {' · '.join(notes)}"


def main() -> int:
    pages = [
        p
        for p in sorted(ROOT.glob("*.html"))
        if not p.name.startswith(SKIP_PREFIX) and p.name not in SKIP_NAMES
    ]
    print("Дизайн-система · плавающий кластер\n")
    for page in pages:
        print("  ✓ " + apply(page))
    skipped = ", ".join(sorted(SKIP_NAMES)) or "—"
    print(f"\nГотово: {len(pages)} страниц. Пропущено: {skipped}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
