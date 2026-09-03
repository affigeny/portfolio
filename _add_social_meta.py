#!/usr/bin/env python3
"""Раскатывает OG- и Twitter-meta по публичным страницам.

Зачем
-----
Без og:* ссылка в Telegram, LinkedIn, WhatsApp и Slack показывается
голо: только URL и домен. Для портфолио это потерянный первый контакт —
собеседник не получает ни имени, ни контекста. Один og:title, og:description
и og:image возвращают к ссылке превью, и читатель видит, о чём страница
до клика.

Аудит зафиксировал отсутствие мета на всех 11 страницах. Скрипт
идемпотентен: перед вставкой снимает ранее поставленный блок, повторный
запуск ничего не дублирует.

Что ставится
------------
- og:type, og:site_name, og:title, og:description, og:image, og:url;
- twitter:card (summary_large_image), title, description, image;
- link rel="canonical" на абсолютный URL.

Значения берутся из существующих <title> и <meta name="description">, а
не выдумываются: og-поля обязаны повторять страницу, а не обещать
что-то другое. og:url — это канонический адрес, и портфолио без него
теряет очки в поиске.

Запуск
------
    python3 _add_social_meta.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://andreevgeny.github.io/portfolio"
SITE_NAME = "Евгений Андреев"
IMAGE_PATH = "assets/og-cover.png"

# Пропускаются служебные файлы с подчёркиванием и OG-карточка, из которой
# саму превью снимать незачем — она и есть изображение.
SKIP_PREFIX = ("_", "proto_", "prototype_", "index_photo")

MARK_OPEN = "<!-- social-meta-v1 -->"
MARK_CLOSE = "<!-- /social-meta-v1 -->"

BLOCK_RE = re.compile(
    re.escape(MARK_OPEN) + r".*?" + re.escape(MARK_CLOSE) + r"\s*",
    re.S,
)


def strip_previous(src: str) -> str:
    return BLOCK_RE.sub("", src)


def extract_meta(text: str) -> tuple[str, str]:
    """Заголовок и описание из существующих тегов."""
    title = re.search(r"<title[^>]*>(.*?)</title>", text, re.S)
    desc = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
        text,
        re.S,
    )
    return (
        title.group(1).strip() if title else SITE_NAME,
        desc.group(1).strip() if desc else "",
    )


def build_block(title: str, description: str, url: str) -> str:
    """Плашка мета-тегов. Готовится одним куском, а не в цикле по строкам:
    девять тегов по одной строке — это двенадцать минут ручной правки
    после первого же добавления поля. Так — две минуты на чтение и
    понятная картинка того, что именно отдаётся в превью."""
    title_e = (title or "").replace("&", "&amp;").replace('"', "&quot;")
    desc_e = (description or "").replace("&", "&amp;").replace('"', "&quot;")
    image = f"{BASE}/{IMAGE_PATH}"

    return f"""{MARK_OPEN}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{title_e}">
<meta property="og:description" content="{desc_e}">
<meta property="og:image" content="{image}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title_e}">
<meta name="twitter:description" content="{desc_e}">
<meta name="twitter:image" content="{image}">
<link rel="canonical" href="{url}">
{MARK_CLOSE}
"""


def page_url(filename: str) -> str:
    if filename == "index.html":
        return f"{BASE}/"
    return f"{BASE}/{filename}"


def apply(path: Path) -> str:
    src = path.read_text(encoding="utf-8")
    src = strip_previous(src)
    title, description = extract_meta(src)
    block = build_block(title, description, page_url(path.name))

    head_close = re.search(r"</head\s*>", src, re.I)
    if not head_close:
        return f"{path.name:26} пропуск: не нашёл </head>"

    src = src[: head_close.start()] + block + src[head_close.start() :]
    path.write_text(src, encoding="utf-8")
    short = description[:60] + "…" if len(description) > 60 else description
    return f"{path.name:26} og + twitter + canonical  ({short or '—'})"


def main() -> int:
    pages = [
        p
        for p in sorted(ROOT.glob("*.html"))
        if not p.name.startswith(SKIP_PREFIX)
    ]
    print("Соц-мета · og:, twitter:, canonical\n")
    for page in pages:
        print("  ✓ " + apply(page))
    print(f"\nГотово: {len(pages)} страниц.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
