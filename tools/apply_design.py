#!/usr/bin/env python3
"""Дизайн-система и плавающий пульт: палитра, шкала 1.618, тема, металл,
   стрелка «далее» к следующему кейсу, иконки контактов.

   Пульт — один ряд в правом нижнем углу, слева направо:
     [GH] [TG] [✉] [☎] │ [металл] [свет|тьма] │ [далее →]

   Почему именно такой порядок
   ---------------------------
   Контакты стоят первыми, а не последними. Пульт читается как строка:
   слева — то, чем страница полезна прямо сейчас, справа — служебное.
   Раньше было наоборот: сначала переключатели дизайна, потом стрелка,
   потом контакты. Человек, который дошёл до конца кейса и хочет
   написать, натыкался сначала на тумблер темы.

   GitHub первый среди контактов: это единственная ссылка, которая
   доказывает сказанное на странице кодом. Telegram — канал прямого
   отклика, поэтому сразу за ним.

   Тема — двусторонний тумблер (div.theme-toggle с двумя кнопками
   data-theme-set), а не одна кнопка с циклом system → light → dark.
   В трёхпозиционном цикле клик «system → light» при системной светлой
   теме визуально ничего не менял: это был пустой клик. assets/theme.js
   слушает только [data-theme-set]; старая разметка button[data-theme-toggle]
   им не обслуживается, и тема на такой странице не переключается вовсе.
   Это и было «пульт сломан»: блок на месте, а клик уходит в никуда.

   Раньше «далее» и контакты жили отдельной плашкой `<aside
   class="next-step">` в подвале: вертикальный столбик с двумя
   смысловыми блоками, и контакты дублировали футер. Скрипт
   `_add_next_step.py` раскатывал её на семь страниц. Теперь её
   функция переехала в плавающий пульт — слитно, гармонично,
   всегда видно. Скрипт заодно снимает старую плашку
   (`<!-- next-step-v1 -->…<!-- /next-step-v1 -->`), так что откат
   возможен повторным запуском старого `_add_next_step.py`.

   Пути
   ----
   assets/css/design.css и assets/js/theme.js. Раньше здесь стояли
   assets/design.css и assets/theme.js: когда файлы разложили по
   подпапкам, скрипт остался на старых путях и при запуске вставил бы
   битые ссылки. Обходить его ручными правками после этого — значит
   держать эталон в десяти файлах и неизбежно что-то пропустить: так
   и вышло, три страницы остались на старой разметке.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CSS_HREF = "assets/css/design.css"
JS_SRC = "assets/js/theme.js"

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
# GitHub — доказательство кодом, Telegram — канал прямого отклика,
# затем почта и телефон. Подробности — в докстринге файла.
CONTACTS = [
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
    """Собирает разметку плавающего пульта для конкретной страницы."""
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
{cx_items}
  <div class="switch-cluster__sep" aria-hidden="true"></div>
  <button class="metal-toggle" type="button" data-metal-toggle aria-label="Акцент: латунь">
    <span class="metal-toggle__icon" aria-hidden="true"></span><span data-metal-label>Латунь</span>
  </button>
  <div class="theme-toggle" data-theme-toggle role="group" aria-label="Тема оформления">
    <button class="theme-toggle__opt" data-theme-set="light" type="button" aria-label="Светлая тема" title="Светлая тема">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="4"/>
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
      </svg>
    </button>
    <button class="theme-toggle__opt" data-theme-set="dark" type="button" aria-label="Тёмная тема" title="Тёмная тема">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
      </svg>
    </button>
    <span class="theme-toggle__ind" aria-hidden="true"></span>
  </div>
{next_html}</div>
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
    """Подключает CSS и тему после авторского <style>: design.css
    переопределяет `:root` по порядку, иначе выиграет страница и
    палитра не соберётся.

    Ищем `</style>` только внутри <head>. Раньше поиск шёл по всему
    документу, и на viral.html — где в конце <body> лежит ещё один блок
    стилей — design.css уезжал в самый последний файла. Страница целиком
    отрисовывалась без дизайн-системы и перекрашивалась, только когда
    парсер доходил до последней строки.
    """
    head_close = re.search(r"</head\s*>", src, re.I)
    span_end = head_close.start() if head_close else len(src)
    matches = list(re.finditer(r"</style\s*>", src[:span_end], re.I))
    if not matches:
        return src, False
    cut = matches[-1].end()
    return src[:cut] + "\n" + chunk + src[cut:], True


def insert_after_head(src: str, chunk: str) -> tuple[str, bool]:
    """Страховка для страниц без <style>: ставим сразу после <head>."""
    head = re.search(r"<head[^>]*>", src, re.I)
    if not head:
        return src, False
    return src[: head.end()] + "\n" + chunk + src[head.end() :], True


def apply(path: Path) -> str:
    src = path.read_text(encoding="utf-8")
    src = strip_previous(src)
    notes: list[str] = []

    # CSS и тема ставятся одним куском и в одном месте: design.css
    # переопределяет палитру страницы, theme.js должен успеть выставить
    # data-theme до первой отрисовки. Разносить их по разным концам
    # <head> незачем, а рассинхрон выглядит как мигание при загрузке.
    chunk = LINK_TAG + "\n" + SCRIPT_TAG
    src, ok = insert_after_last_style(src, chunk)
    if not ok:
        src, ok = insert_after_head(src, chunk)
        if not ok:
            return f"{path.name:26} пропуск: не нашёл ни <style>, ни <head>"
        notes.append("нет <style>")
    else:
        notes.append("css+тема")

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
