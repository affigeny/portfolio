#!/usr/bin/env python3
"""Генерирует changelog из NEXT_STEPS.md §4.

Зачем
-----
OVERVIEW.html §02 «Меню изменений» — ручная копия из NEXT_STEPS.md §4.
При каждой новой сессии легко забыть синхронизировать. Скрипт парсит
§4.x и выдаёт сводку (номер, заголовок, первая строка описания).
Сводку можно сверить с OVERVIEW.html и дополнить, если что-то
пропущено.

Использование
------------
    python3 _changelog.py
    python3 _changelog.py --since 4.4   # только сессии 4.4 и новее

Что выдаёт
---------
Список сессий в формате:

    §4.6 · Что сделано 2 сентября, седьмая сессия (ночь, продолжение)
      Шапка: Что сделано 2 сентября, седьмая сессия (ночь, продолжение)
      Первая строка: По вашему «давай дальше» и пожеланию держать ...

Плюс сводка: сколько сессий, какие диапазоны.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# NEXT_STEPS.md больше не лежит рядом: после закрытия P0 внутренние
# документы живут в Obsidian, а в репозитории остались только страницы.
# Путь задаётся аргументом --file или переменной окружения NEXT_STEPS;
# значение по умолчанию — папка проекта в хранилище.
VAULT_NEXT_STEPS = (
    Path.home()
    / "Library/Mobile Documents/iCloud~md~obsidian/Documents/VAULT-2"
    / "Мои РЕЗЮМЕ/проект-портфолио/NEXT_STEPS.md"
)
NEXT_STEPS = Path(
    os.environ.get("NEXT_STEPS") or VAULT_NEXT_STEPS
).expanduser()

# `## 4.6 · Что сделано 2 сентября, седьмая сессия (ночь, продолжение)`
SECTION_RE = re.compile(
    r"^##\s*(?P<num>\d+(?:\.\d+)?)\s*·\s*(?P<title>.+?)\s*$",
    re.MULTILINE,
)


def parse_sections(text: str) -> list[dict]:
    """Парсит все `## 4.x` секции из NEXT_STEPS.md.

    Возвращает список словарей с полями:
      - num: «4.6»
      - title: полный заголовок
      - body: текст секции до следующей `##`
      - first_line: первая содержательная строка тела
      - char_count: длина тела
    """
    matches = list(SECTION_RE.finditer(text))
    sections: list[dict] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        first_line = ""
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
                continue
            if line.startswith(("**", "---", "###", "—", "-")):
                continue
            first_line = line
            break
        sections.append(
            {
                "num": m.group("num"),
                "title": m.group("title").strip(),
                "body": body,
                "first_line": first_line,
                "char_count": len(body),
            }
        )
    return sections


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--since",
        help="Показать только сессии с этого номера и новее (например, 4.4)",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=NEXT_STEPS,
        help="Путь к NEXT_STEPS.md (по умолчанию — папка проекта в Obsidian)",
    )
    args = parser.parse_args()

    if not args.path.exists():
        print(f"Файл не найден: {args.path}", file=sys.stderr)
        return 1

    text = args.path.read_text(encoding="utf-8")
    sections = parse_sections(text)

    if args.since:
        sections = [s for s in sections if s["num"] >= args.since]

    # Только секции уровня ## 4.x (не ## 1, ## 2, и т.д.)
    sections = [s for s in sections if s["num"].startswith("4.")]

    if not sections:
        print(f"Сессий с §4.x не найдено (фильтр: --since={args.since})", file=sys.stderr)
        return 1

    print(f"Найдено сессий: {len(sections)}")
    print(f"Диапазон: §{sections[0]['num']} — §{sections[-1]['num']}")
    print()
    for s in sections:
        print(f"§{s['num']} · {s['title']}")
        if s["first_line"]:
            first = s["first_line"]
            if len(first) > 120:
                first = first[:117] + "..."
            print(f"  {first}")
        print(f"  размер: {s['char_count']} символов")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
