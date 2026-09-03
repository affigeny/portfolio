#!/usr/bin/env python3
"""Приводит страницы к эталону там, где одного design.css недостаточно.

Почему скрипт, а не правка руками
---------------------------------
`assets/design.css` переопределяет токены, но не может поправить
значения, прописанные прямо в правилах страницы: межстрочный интервал
заголовка, цвет внутри градиента, состав подключённых гарнитур. Эти
значения лежат в восьми файлах и расходятся между собой — отсюда
ощущение «криво»: на одной странице заголовок дышит, на другой строки
наезжают друг на друга.

Править их руками — значит держать в голове восемь файлов и неизбежно
что-то пропустить. Скрипт делает правку один раз, одинаково для всех,
и оставляет след в отчёте: что и где изменено.

Что именно чинит
----------------
1. **Межстрочный интервал заголовков.** `line-height` меньше 1.0 при
   кегле 60–96 px даёт строку короче самого кегля: вторая строка
   наезжает на первую. Узкий капс Oswald визуально терпит 1.02 — на
   этом значении и остановились. Декоративные цифры секций (`.sec-num`)
   не трогаем: они однострочные, столкнуться там нечему.
2. **Цвет свечения первого экрана.** Страницы держали в градиенте
   оранжевый `oklch(28% .06 45)`, а акцент эталона — латунь (тон 80).
   Оранжевое свечение под латунными ссылками — это и есть «нет
   гармонии». Тон приводится к акцентному, геометрия градиента
   сохраняется: двигается только цвет, а не размеры пятна.
3. **Состав гарнитур.** IBM Plex Mono подключён не везде, и на
   страницах без него служебный текст (даты, надзаголовки, метки)
   отрисовывается системным моноширинным — другим по начертанию и по
   ширине. Отсюда «шрифты странны».

Запуск
------
    python3 _harmonize_pages.py

Идемпотентен: перед заменой проверяет, что старое значение ещё на
месте; повторный запуск ничего не меняет и пишет «без изменений».
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Страницы, которые не публикуются и в обход не идут.
SKIP_NAMES = {"OVERVIEW.html"}

# ── 1. Межстрочный интервал ───────────────────────────────────────────
# (файл, что ищем, на что меняем). Ищем с привязкой к селектору, чтобы
# не задеть декоративные элементы с таким же интервалом.
LINE_HEIGHT_FIXES: list[tuple[str, str, str]] = [
    ("index.html", ".display{font-family:'Oswald',Impact,sans-serif;line-height:.92;",
     ".display{font-family:'Oswald',Impact,sans-serif;line-height:1.02;"),
    ("models.html", "h1{font-size:clamp(36px,5.6vw,58px);line-height:.98;",
     "h1{font-size:clamp(36px,5.6vw,58px);line-height:1.02;"),
    ("qa.html", ".display{font-family:'Oswald',Impact,sans-serif;line-height:.9;",
     ".display{font-family:'Oswald',Impact,sans-serif;line-height:1.02;"),
    ("qa.html", "h2.sec-title{font-family:'Oswald',sans-serif;font-size:clamp(32px,4.6vw,60px);line-height:.9;",
     "h2.sec-title{font-family:'Oswald',sans-serif;font-size:clamp(32px,4.6vw,60px);line-height:1.02;"),
    ("sorterlab.html", "h1{font-size:clamp(48px,7vw,96px);line-height:.93;",
     "h1{font-size:clamp(48px,7vw,96px);line-height:1.02;"),
    ("sorterlab.html", "h2{font-size:clamp(38px,5.5vw,72px);line-height:.9;",
     "h2{font-size:clamp(38px,5.5vw,72px);line-height:1.02;"),
    ("sorterlab-simulator.html", "h1{font-size:clamp(30px,4.2vw,62px);line-height:.96;",
     "h1{font-size:clamp(30px,4.2vw,62px);line-height:1.02;"),
    ("ux.html", "letter-spacing:-.02em;line-height:.94}",
     "letter-spacing:-.02em;line-height:1.02}"),
    ("ux.html", "h2{font-family:'Oswald',sans-serif;text-transform:uppercase;font-size:clamp(34px,5vw,66px);line-height:.9;",
     "h2{font-family:'Oswald',sans-serif;text-transform:uppercase;font-size:clamp(34px,5vw,66px);line-height:1.02;"),
    ("value.html", ".display{font-family:'Oswald',Impact,sans-serif;line-height:.88;",
     ".display{font-family:'Oswald',Impact,sans-serif;line-height:1.02;"),
    ("value.html", "h2.sec-title{font-family:'Oswald',sans-serif;font-size:clamp(34px,5vw,68px);line-height:.9;",
     "h2.sec-title{font-family:'Oswald',sans-serif;font-size:clamp(34px,5vw,68px);line-height:1.02;"),
    ("viral.html", "h2.sec-title{font-family:'Oswald',sans-serif;font-size:clamp(38px,6vw,86px);line-height:.86;",
     "h2.sec-title{font-family:'Oswald',sans-serif;font-size:clamp(38px,6vw,86px);line-height:1.02;"),
]

# ── 2. Тон свечения ───────────────────────────────────────────────────
# Оранжевый (тон 45) -> латунный (тон 80). Альфа и геометрия сохраняются,
# поэтому заменяется только цвет, без пересборки всего градиента.
GLOW_RE = re.compile(r"oklch\(28%\s*(?:0\.06|\.07)\s*45(?P<alpha>/\.[\d]+)\)")

# ── 3. Гарнитуры ──────────────────────────────────────────────────────
FONTS_FULL = (
    '<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700'
    '&family=Golos+Text:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600'
    '&display=swap" rel="stylesheet">'
)

# Страницы, где моноширинная гарнитура не подключена вовсе: служебный
# текст там отрисовывается системным шрифтом и выпадает из единого вида.
MONO_MISSING = {
    "archetypes.html": (
        '<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700'
        '&family=Golos+Text:wght@400;500;600;700&display=swap" rel="stylesheet">'
    ),
    "writing.html": (
        '<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700'
        '&family=Golos+Text:wght@400;500;600;700&display=swap" rel="stylesheet">'
    ),
}

# Симулятор не подключает ничего: живёт на системных шрифтах.
FONTS_ABSENT = ("sorterlab-simulator.html",)


def fix_line_heights(path: Path) -> list[str]:
    """Поднимает межстрочный интервал заголовков до 1.02."""
    src = path.read_text(encoding="utf-8")
    done = []
    for name, old, new in LINE_HEIGHT_FIXES:
        if name != path.name or old not in src:
            continue
        src = src.replace(old, new, 1)
        done.append(f"интервал {old[old.find('line-height'):][:16]}")
    if done:
        path.write_text(src, encoding="utf-8")
    return done


def fix_glow(path: Path) -> int:
    """Перекрашивает свечение первого экрана в тон акцента."""
    src = path.read_text(encoding="utf-8")
    src_new, count = GLOW_RE.subn(lambda m: f"oklch(28% .045 80{m.group('alpha')})", src)
    if count:
        path.write_text(src_new, encoding="utf-8")
    return count


def fix_fonts(path: Path) -> str:
    """Подключает недостающие гарнитуры."""
    src = path.read_text(encoding="utf-8")

    if path.name in MONO_MISSING:
        old = MONO_MISSING[path.name]
        if old in src and "IBM+Plex+Mono" not in src:
            src = src.replace(old, FONTS_FULL, 1)
            path.write_text(src, encoding="utf-8")
            return "+ IBM Plex Mono"

    if path.name in FONTS_ABSENT:
        head = re.search(r"<head[^>]*>", src, re.I)
        if head and "fonts.googleapis.com" not in src:
            src = src[: head.end()] + "\n" + FONTS_FULL + src[head.end() :]
            # Симулятор держал font-family на body/system-ui — эталонные
            # гарнитуры подхватываются из design.css, но только если
            # страница не задаёт свои. Снимаем явное указание.
            src = src.replace(
                "font-family:system-ui,-apple-system,\"Segoe UI\",sans-serif",
                "font-family:'Golos Text',system-ui,sans-serif",
            )
            path.write_text(src, encoding="utf-8")
            return "+ Oswald / Golos / Plex Mono"

    return ""


def main() -> int:
    pages = [
        p
        for p in sorted(ROOT.glob("*.html"))
        if not p.name.startswith(("_", "proto_", "prototype_", "index_photo"))
        and p.name not in SKIP_NAMES
    ]

    print("Приведение страниц к эталону\n")
    total = 0
    for page in pages:
        notes: list[str] = []
        notes += fix_line_heights(page)

        glow = fix_glow(page)
        if glow:
            notes.append(f"свечение ×{glow}")

        fonts = fix_fonts(page)
        if fonts:
            notes.append(fonts)

        if notes:
            total += len(notes)
            print(f"  ✓ {page.name:26} " + " · ".join(notes))
        else:
            print(f"  · {page.name:26} без изменений")

    print(f"\nГотово: {total} правок на {len(pages)} страницах.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
