#!/usr/bin/env python3
"""Ловит оборванные правки CSS до того, как их увидит браузер.

Зачем
-----
Парсер CSS в Chrome выбрасывает правила с битым селектором молча:
страница собирается без них, и ошибка проявляется только визуально
(«фильтр стал другого цвета», «контакт в футере слился с фоном»).
В одной ночной сессии 03.09 такой класс ошибки приключился четыре
раза подряд в `assets/design.css`:

  1. Висячий селектор `html[data-theme="light"] .filter-row` склеился
     со следующим правилом в список-потомок html внутри html, который
     ничему не соответствует. Соседние правила перестали применяться.
  2. Висячий `html[data-theme="light"]` перед группой селекторов —
     тот же эффект.
  3. Снятие мёртвого `.controls` в @media print склеило список
     «скрыть кнопки» с правилом «вернуть подписи контактов на бумаге»,
     и кнопки поехали в распечатку.
  4. Снятие `.fin-sep` оставило осиротевший комментарий, описывающий
     несуществующий разделитель.

Каждый из четырёх случаев проходил через `_check_contrast.py` и
`_probe_contrast.py` как «поломанный элемент в DOM с контрастом
ниже порога» — диагноз был, а причина плыла мимо. Этот скрипт
проверяет синтаксическую целостность CSS до замера контраста.

Что ловит
---------
- Висящий селектор перед `{` (селектор заканчивается запятой).
- Пустой селектор в списке.
- Двойной `html[...]` в одном составном селекторе (html внутри html
  в потомках — частый маркер склейки).
- Нарушенный баланс фигурных скобок.

Проверка «класс упомянут в комментарии, но не в правилах» есть
(флаг `--orphans`), но по умолчанию выключена: слишком много
легитимных упоминаний (`.anim`, `.brand`, имена файлов, ссылки
на `models.html`).

Запуск
------
    python3 _check_css.py                       # один файл по умолчанию
    python3 _check_css.py assets/css/design.css # конкретный путь
    python3 _check_css.py --all                 # все .css в проекте
    python3 _check_css.py --all --orphans       # + упомянутые классы

Идемпотентен. Возвращает код 0 при чистом CSS, 1 при находках.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# CSS-комментарии — с сохранением числа переносов строк, чтобы
# номера строк ниже совпадали с исходником.
def _strip_comments(src: str) -> str:
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)


def check_one(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    findings: list[str] = []

    # Баланс скобок
    depth = 0
    for i, ch in enumerate(src):
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                findings.append(f"  строка ~{src[:i].count(chr(10)) + 1}: лишняя `}}`")
                depth = 0
    if depth != 0:
        findings.append(f"  баланс скобок нарушен: depth={depth} (не хватает {'}' * depth})")

    clean = _strip_comments(src)

    # Список правил верхнего уровня
    rules: list[tuple[int, int, str]] = []  # (open_pos, close_pos, selector)
    depth, start = 0, None
    for i, ch in enumerate(clean):
        if ch == "{":
            if depth == 0: start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                # Найти селектор: от предыдущей `}` (или 0) до `{`
                prev_close = clean.rfind("}", 0, start)
                sel = clean[prev_close + 1:start]
                rules.append((start, i, sel))
            elif depth == 0:
                start = None

    for n, (o, _c, sel) in enumerate(rules):
        line = clean[:o].count(chr(10)) + 1
        s = re.sub(r"\s+", " ", sel).strip()
        if s.endswith(","):
            findings.append(f"  строка {line}: селектор оканчивается запятой → `…{s[-60:]}`")
        for part in s.split(","):
            p = part.strip()
            if not p:
                findings.append(f"  строка {line}: пустой селектор в списке")
            if p.count("html[") > 1:
                findings.append(f"  строка {line}: `html[...]` встречается {p.count('html[')} раз в одном селекторе → `{p}`")

    # Осиротевшие комментарии — за флагом, см. --orphans.
    if "--orphans" in sys.argv:
        mentioned = set(re.findall(r"\.([A-Za-z_][\w-]*)", "\n".join(m.group(0) for m in re.finditer(r"/\*.*?\*/", src, flags=re.S))))
        used: set[str] = set()
        for _o, _c, sel in rules:
            for m in re.findall(r"\.([A-Za-z_][\w-]*)", sel):
                used.add(m)
        orphans = sorted(mentioned - used)
        if orphans:
            findings.append("  P1 · в комментариях упомянуты классы без правил в файле: " + ", ".join(f".{c}" for c in orphans))

    return findings


def main() -> int:
    if "--all" in sys.argv:
        paths = sorted(ROOT.rglob("*.css"))
        # Архив и черновики — не для прод-проверки. Там могут
        # лежать как раз сломанные версии, на которых мы учились.
        paths = [p for p in paths if "/_archive/" not in str(p) and "/_drafts/" not in str(p)]
    else:
        arg = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
        paths = [Path(arg)] if arg else [ROOT / "assets/css/design.css"]

    rc = 0
    for p in paths:
        if not p.exists():
            print(f"  ! {p}: не найден")
            rc = 1
            continue
        bad = check_one(p)
        if bad:
            print(f"✗ {p}")
            for line in bad:
                print(line)
            rc = 1
        else:
            print(f"✓ {p}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
