#!/usr/bin/env python3
"""Собирает HTML-версии резюме из markdown-исходников в resumes/.

Почему скрипт, а не ручная вёрстка шести страниц
------------------------------------------------
Файлы в resumes/ собираются из RESUME_MASTER.md и не правятся напрямую —
это правило уже записано в мастере. Если HTML верстать руками, появляется
второй источник фактов, и он расходится с первым: правка в мастере
доедет до markdown и не доедет до HTML. Так уже один раз произошло —
старые резюме держали Роболаторию за 2021–2024 вместо 2018–2020 и
«отдел 5 человек» вместо «4 месяца до трёх».

Поэтому HTML генерируется: поменяли markdown → перезапустили → обе версии
одинаковы по фактам, различаются только подачей.

Почему файлы самодостаточные, без assets/
-----------------------------------------
Резюме скачивают, пересылают вложением, открывают без сети. Страница,
которая рассыпается без внешнего CSS, не выполняет свою работу. Токены,
тема и гарнитуры повторяют assets/design.css, но встроены в файл.

Запуск
------
    python3 _build_resume_html.py

Скрипт идемпотентен: перезапуск перезаписывает HTML целиком.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "resumes"

# Секции, которые уходят в узкую колонку и на всю ширину. Остальное —
# в основную колонку. Раскладка основной колонки к узкой: 1 : 0.618,
# то есть 61.8 % на 38.2 %.
RAIL_SECTIONS = {"Инструменты", "Образование", "Условия"}
WIDE_SECTIONS = {"Открытые артефакты"}

# Ссылки в таблице артефактов записаны без протокола: github.com/... —
# иначе в markdown они выглядят как мусор. Здесь они превращаются в
# настоящие ссылки, чтобы рекрутер дошёл до репозитория в один клик.
BARE_URL = re.compile(
    r"^(?:https?://)?((?:github\.com|andreevgeny\.github\.io|t\.me|linkedin\.com)"
    r"/[\w./?#&%=-]*)$"
)


# ── Разбор markdown ────────────────────────────────────────────────────


def inline(text: str) -> str:
    """Жирный, курсив и код внутри строки.

    Экранирование — первым: иначе угловые скобки из текста превратятся
    в разметку, а кавычки в атрибутах поедут.
    """
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`(.+?)`", r"<code>\1</code>", out)
    out = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<em>\1</em>", out)
    return out


def linkify(cell: str) -> str:
    """Голый адрес в ячейке таблицы — в ссылку."""
    match = BARE_URL.match(cell.strip())
    if not match:
        return inline(cell)
    url = "https://" + match.group(1)
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(match.group(1))}</a>'


def parse(text: str) -> dict:
    """Markdown → промежуточная структура.

    Поддержан ровно тот набор конструкций, который реально встречается
    в шести файлах: заголовки трёх уровней, абзацы, списки, таблицы,
    цитаты, разделители и жирная строка вида «период · место». Ничего
    сверх этого — недоделанный парсер лучше, чем универсальный, который
    на половине файлов молча выдаёт чушь.
    """
    doc: dict = {
        "h1": "",
        "h2": "",
        "contacts": "",
        "lead": [],
        "sections": [],
        "footer": "",
    }
    current: dict | None = None
    paragraph: list[str] = []
    quote: list[str] = []
    table: list[str] = []
    bullets: list[str] = []
    mode = "p"
    awaiting_contacts = False

    def flush() -> None:
        nonlocal paragraph, quote, table, bullets, mode
        if paragraph:
            # Текст до первого раздела — не содержание резюме, а служебная
            # инструкция себе. Без этой ветки он молча пропадал: flush()
            # складывал абзац только внутрь раздела.
            if current is None:
                doc["lead"].extend(paragraph)
            else:
                current["blocks"].append(("p", " ".join(paragraph)))
        if quote and current is not None:
            current["blocks"].append(("quote", quote))
        if table and current is not None:
            current["blocks"].append(("table", table))
        if bullets and current is not None:
            current["blocks"].append(("ul", bullets))
        paragraph, quote, table, bullets = [], [], [], []
        mode = "p"

    for raw in text.split("\n"):
        line = raw.rstrip()

        # Раздел третьего уровня открывается и без уже открытого: первый
        # `###` в файле приходит, когда current ещё None. С прежней
        # проверкой `and current is not None` он проваливался в абзац,
        # и страница собиралась вообще без разделов.
        if line.startswith("### "):
            flush()
            current = {"title": line[4:].strip(), "blocks": []}
            doc["sections"].append(current)
            continue

        if line.startswith("## "):
            flush()
            body = line[3:].strip()
            # В файлах резюме второй уровень — это строка с именем, а не
            # раздел: `## Евгений Андреев · Москва и МО · удалёнка`.
            # В шпаргалке вторым уровнем идут разделы. Различаем по
            # содержимому, а не по порядку: на позицию полагаться нельзя.
            if not doc["h2"] and "Евгений Андреев" in body:
                doc["h2"] = body
                awaiting_contacts = True
                continue
            doc["sections"].append({"title": body, "blocks": []})
            current = doc["sections"][-1]
            continue

        if line.startswith("# "):
            doc["h1"] = line[2:].strip()
            continue

        if line.strip() == "---":
            flush()
            continue

        if not line.strip():
            flush()
            continue

        # Сразу после строки с именем идёт строка контактов.
        if awaiting_contacts and not line.startswith(("#", "|", ">")):
            doc["contacts"] = line.strip()
            awaiting_contacts = False
            continue

        if line.startswith("|"):
            if mode != "table":
                flush()
                mode = "table"
            table.append(line)
            continue

        if line.startswith("> "):
            if mode != "quote":
                flush()
                mode = "quote"
            quote.append(line[2:].strip())
            continue

        if line.startswith("- "):
            if mode != "ul":
                flush()
                mode = "ul"
            bullets.append(line[2:].strip())
            continue

        paragraph.append(line.strip())
        mode = "p"

    flush()

    # Итоговая строка курсивом — служебная пометка об источнике, не
    # содержание резюме. Уходит в подвал.
    for section in doc["sections"]:
        kept = []
        for kind, payload in section["blocks"]:
            if kind == "p" and payload.startswith("*Собрано из"):
                doc["footer"] = payload.strip("*")
            else:
                kept.append((kind, payload))
        section["blocks"] = kept
    return doc


def split_bold_span(text: str) -> tuple[str, str]:
    """«**период · роль** описание» → («период · роль», «описание»).

    В markdown файлов резюме строка опыта записана так: жирная шапка
    одной строкой, описание — следующей. Парсер склеивает соседние
    строки в один абзац, поэтому закрывающая «**» оказывается внутри
    строки, и `strip("*")` её не трогает: она снимает символы только с
    концов. Раньше из-за этого описание уезжало внутрь `<h3>` вместе с
    сырыми звёздочками, и весь блок опыта получался жирным.

    Ищем закрывающую пару, а не последнюю звезду: одиночная «*» внутри
    текста — это курсив, а не конец шапки.
    """
    if not text.startswith("**"):
        return text, ""
    close = text.find("**", 2)
    if close == -1:
        return text, ""
    return text[2:close].strip(), text[close + 2 :].strip()


def split_period(title: str) -> tuple[str, str]:
    """«2024 — сейчас · Собственные AI-продукты» → («2024 — сейчас», «…»).

    Жирная строка с точкой с запятой-разделением — это строка опыта.
    Разделитель ровно один, и он первый: названия вроде «АО „Одинцовская
    теплосеть" · инженер» тоже содержат « · », поэтому важно не резать
    по всем вхождениям.
    """
    if " · " not in title:
        return "", title
    when, what = title.split(" · ", 1)
    return when.strip(), what.strip()


def split_job(title: str) -> tuple[str, str, str]:
    """«период · место · роль» → («период», «место», «роль»).

    Жирным в строке опыта должно быть одно название — место, как и в
    таблице опыта на `index.html`, где колонка так и называется:
    «Роль и место», и первой идёт организация. Раньше `split_period`
    резал только по первому « · », поэтому в `<h3>` уезжали и место,
    и должность сразу: получалась жирная простыня из восьмидесяти
    знаков, в которой название терялось.

    Частей бывает две или три. Две — когда роль уже внутри названия
    («Школа-студия прикладного искусства, основатель»); тогда роль
    пустая, и жирным остаётся само название. Роль склеиваем обратно
    по всем вхождениям: внутри должности « · » тоже встречается
    («инженер → руководитель направления развития»).
    """
    parts = [part.strip() for part in title.split(" · ") if part.strip()]
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return parts[0], parts[1], " · ".join(parts[2:])


# ── Сборка HTML ────────────────────────────────────────────────────────

TOKENS_DARK = """
:root,
html[data-theme="dark"] {
  --bg: #0a0a0b;      --bg-2: #101012;
  --surface: #141416; --surface-2: #1a1a1d;
  --line: #26262a;    --line-strong: #34343a;

  --text: #f2f0ec;  --muted: #a5a19a;  --dim: #8d887f;
  --accent: #c9a96a;  --accent-hover: #d8bb80;
  --accent-soft: rgba(201, 169, 106, 0.14);
  --accent-line: rgba(201, 169, 106, 0.38);
  --on-accent: #0a0a0b;

  --ok: #6fae86;  --warn: #d9a05b;  --bad: #cf6f6f;

  --r: 14px;  --r-lg: 22px;

  /* Шкала 1.618. Ступени идут через √φ = 1.272: чистый φ на соседних
     ступенях даёт скачок, на котором рвётся ритм. */
  --s1: 0.382rem; --s2: 0.618rem; --s3: 1rem;
  --s4: 1.618rem; --s5: 2.618rem; --s6: 4.236rem;

  --t0: 0.791rem; --t1: 0.875rem; --t2: 1rem;   --t3: 1.125rem;
  --t4: 1.272rem; --t5: 1.618rem; --t6: 2.058rem; --t7: 2.618rem;

  --pad: clamp(18px, 4vw, 44px);
  --shell: min(1180px, calc(100% - var(--pad) * 2));
  --ease: cubic-bezier(0.16, 1, 0.3, 1);

  --font-body: "Golos Text", system-ui, -apple-system, sans-serif;
  --font-display: "Oswald", "Golos Text", system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;

  color-scheme: dark;
}
"""

TOKENS_LIGHT = """
  --bg: #fbfaf8;      --bg-2: #f4f2ee;
  --surface: #ffffff; --surface-2: #f7f5f1;
  --line: #e4e0d9;    --line-strong: #d2cdc4;

  --text: #1a1917;  --muted: #5e5a53;  --dim: #6f6a61;
  --accent: #8a6d2f;  --accent-hover: #6f5726;
  --accent-soft: rgba(138, 109, 47, 0.1);
  --accent-line: rgba(138, 109, 47, 0.34);
  --on-accent: #ffffff;

  --ok: #3f7d57;  --warn: #8a5f22;  --bad: #a84444;

  color-scheme: light;
"""

CSS = """
*, *::before, *::after { box-sizing: border-box; }

html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: var(--t2);
  line-height: 1.618;
  letter-spacing: -0.005em;
  /* Лигатуры выключены: в моноширинном ffi в «andreevgeny» склеивается
     в один глиф, и адрес, скопированный из PDF, ведёт на 404. */
  font-variant-ligatures: none;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hover); }

:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }

::selection { background: var(--accent); color: var(--on-accent); }

.page { width: var(--shell); margin-inline: auto; padding-block: var(--s5) var(--s6); }

/* ── Шапка ──────────────────────────────────────────────────────────
   Имя крупнее роли: читатель ищет фамилию, а не должность. Раскладка
   снова 1 : 0.618 — текст слева, контакты справа. */
.hd {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 0.618fr);
  gap: var(--s4);
  align-items: end;
  padding-bottom: var(--s4);
  margin-bottom: var(--s5);
  border-bottom: 1px solid var(--line-strong);
}

.name {
  font-family: var(--font-display);
  font-size: var(--t7);
  font-weight: 500;
  line-height: 1;
  letter-spacing: -0.015em;
  margin: 0 0 var(--s2);
}

.role {
  font-family: var(--font-mono);
  font-size: var(--t3);
  color: var(--accent);
  margin: 0 0 var(--s2);
}

.meta {
  font-family: var(--font-mono);
  font-size: var(--t1);
  color: var(--muted);
  margin: 0;
}

/* Контакты — текстом, а не иконками. Здесь обратная логика к страницам
   сайта: резюме нужно затем, чтобы читатель мог дотянуться. */
.ct { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--s1); }
.ct li { font-family: var(--font-mono); font-size: var(--t1); }
.ct a { color: var(--text); border-bottom: 1px solid var(--accent-line); }
.ct a:hover { color: var(--accent); }

/* ── Раскладка ────────────────────────────────────────────────────── */
/* Одна колонка на всю ширину. Две («main rail») здесь были и давали
   ровно то, что заметил Евгений при вычитке: содержание узкой колонки
   кончалось на трети высоты, и дальше «Опыт» шёл с пустым полем
   справа. Раскладка, которая держится на том, хватит ли коротких
   разделов по высоте под длинные, не переживает правки текста — а
   резюме правят при каждом отклике.

   Справочные разделы (инструменты, образование, условия) поэтому
   уходят в горизонтальную полосу внизу: пустоты нет по построению,
   при любом объёме текста и при любой печати. Пропорция 1 : 0.618
   из `DESIGN_STANDARD.md` живёт не здесь, а в шапке и в сетке строк
   опыта (1 : 4.236) — там, где она не зависит от длины текста. */
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  row-gap: var(--s5);
}
.col-rail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: var(--s5);
  align-items: start;
  padding-top: var(--s4);
  border-top: 1px solid var(--line);
}

.sec { margin-bottom: var(--s5); }
.sec:last-child { margin-bottom: 0; }

.h {
  display: flex;
  align-items: baseline;
  gap: var(--s2);
  margin: 0 0 var(--s3);
  padding-bottom: var(--s2);
  border-bottom: 1px solid var(--line);
  font-family: var(--font-mono);
  font-size: var(--t1);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--dim);
}
.h::before {
  content: "";
  width: 18px; height: 1px;
  background: var(--accent);
  flex: none;
  transform: translateY(-0.35em);
}

/* ── Опыт ───────────────────────────────────────────────────────────
   Даты отдельным столбцом: хронология считывается одним движением
   взгляда, не вычитываясь из текста. Пропорция 1 : 4.236 = φ³. */
.job {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 4.236fr);
  gap: var(--s2) var(--s3);
  padding-block: var(--s3);
  border-bottom: 1px solid var(--line);
}
.job:last-child { border-bottom: none; }

.job__when {
  font-family: var(--font-mono);
  font-size: var(--t1);
  color: var(--dim);
  padding-top: 0.15em;
}
.job__what h3 {
  font-family: var(--font-body);
  font-size: var(--t3);
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 var(--s1);
}
/* Должность — акцентом, место нейтрально. Раньше жирным шло всё
   сразу: и место, и должность, и глаз не цеплялся ни за что. Теперь
   название читается как название, а подсвечена способность — та же
   логика, по которой резюме продаёт способность, а не носитель. */
.job__role {
  margin: 0 0 var(--s2);
  font-size: var(--t1);
  color: var(--accent);
  font-weight: 500;
}
.job__what p { margin: 0 0 var(--s2); font-size: var(--t1); color: var(--muted); }
.job__what p:last-child { margin-bottom: 0; }

/* ── Списки ───────────────────────────────────────────────────────── */
.bul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--s3); }
.bul li { position: relative; padding-left: var(--s4); font-size: var(--t1); color: var(--muted); }
.bul li::before {
  content: "";
  position: absolute; left: 0; top: 0.62em;
  width: 6px; height: 6px;
  border: 1px solid var(--accent);
  transform: rotate(45deg);
}
.bul strong { color: var(--text); font-weight: 600; }

.lead-p { margin: 0 0 var(--s2); font-size: var(--t3); color: var(--muted); max-width: 62ch; }

.txt { margin: 0 0 var(--s2); font-size: var(--t1); color: var(--muted); }
.txt:last-child { margin-bottom: 0; }
.txt strong { color: var(--text); }

/* ── Таблица артефактов ───────────────────────────────────────────── */
.tbl-wrap { overflow-x: auto; }
.tbl { width: 100%; border-collapse: collapse; font-size: var(--t1); }
.tbl th {
  font-family: var(--font-mono);
  font-size: var(--t0);
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--dim);
  text-align: left;
  padding-bottom: var(--s2);
  border-bottom: 1px solid var(--line-strong);
}
.tbl td {
  padding: var(--s2) var(--s3) var(--s2) 0;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
  color: var(--muted);
}
.tbl tr:last-child td { border-bottom: none; }
.tbl td:first-child { color: var(--text); font-weight: 600; white-space: nowrap; }
.tbl a {
  font-family: var(--font-mono);
  font-size: var(--t0);
  border-bottom: 1px solid var(--accent-line);
  word-break: break-all;
}

/* ── Цитата и копирование (шпаргалка) ─────────────────────────────── */
.q {
  position: relative;
  margin: 0 0 var(--s4);
  padding: var(--s4);
  background: var(--surface);
  border: 1px solid var(--line);
  border-left: 2px solid var(--accent);
  border-radius: 0 var(--r) var(--r) 0;
}
.q p { margin: 0 0 var(--s2); line-height: 1.618; }
.q p:last-child { margin-bottom: 0; }
.q__copy {
  position: absolute; top: var(--s2); right: var(--s2);
  padding: 5px 11px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--bg-2);
  color: var(--dim);
  font-family: var(--font-mono);
  font-size: var(--t0);
  cursor: pointer;
  transition: color 0.2s var(--ease), border-color 0.2s var(--ease);
}
.q__copy:hover { color: var(--accent); border-color: var(--accent-line); }
.q__copy.is-ok { color: var(--ok); border-color: var(--ok); }

/* ── Служебная заметка ────────────────────────────────────────────── */
.note {
  margin: 0 0 var(--s4);
  padding: var(--s3) var(--s4);
  background: var(--surface-2);
  border-left: 2px solid var(--warn);
  font-size: var(--t1);
  color: var(--muted);
}

/* ── Подвал ───────────────────────────────────────────────────────── */
.ft {
  margin-top: var(--s5);
  padding-top: var(--s3);
  border-top: 1px solid var(--line);
  font-family: var(--font-mono);
  font-size: var(--t0);
  color: var(--dim);
}

/* ── Переключатель темы ───────────────────────────────────────────── */
.tt {
  position: fixed;
  right: clamp(14px, 3vw, 28px);
  bottom: clamp(14px, 3vw, 28px);
  z-index: 99;
  display: inline-flex;
  align-items: center;
  gap: var(--s2);
  padding: 9px 15px;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: var(--t0);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  transition: color 0.2s var(--ease), border-color 0.2s var(--ease);
}
.tt:hover { color: var(--accent); border-color: var(--accent-line); }
.tt__i {
  width: 12px; height: 12px;
  border-radius: 50%;
  border: 1.5px solid currentColor;
  flex: none;
}
html[data-theme="dark"] .tt__i,
html[data-theme="system"] .tt__i { background: linear-gradient(to right, currentColor 0 50%, transparent 50% 100%); }
html[data-theme="light"] .tt__i { background: currentColor; }

@media (max-width: 900px) {
  .grid { row-gap: var(--s4); }
  .col-rail { grid-template-columns: 1fr; gap: var(--s4); }
  .hd { grid-template-columns: 1fr; align-items: start; }
  .job { grid-template-columns: 1fr; gap: var(--s1); }
}

@media (prefers-reduced-motion: reduce) {
  * { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }
}

/* ── Печать ───────────────────────────────────────────────────────────
   Резюме печатают и шлют PDF. Печать всегда светлая: тёмный фон съедает
   тонер и читается хуже на экране рекрутера. */
@media print {
  :root {
    --bg: #ffffff; --bg-2: #ffffff;
    --surface: #ffffff; --surface-2: #f6f5f2;
    --line: #d9d5cd; --line-strong: #b9b5ad;
    --text: #14130f; --muted: #45423c; --dim: #5c5952;
    --accent: #6f5726; --accent-line: #b9b5ad; --accent-soft: transparent;
  }
  @page { size: A4; margin: 13mm 12mm; }

  html, body { background: #ffffff !important; color: #14130f !important; }
  body { font-size: 9.6pt; line-height: 1.5; }

  .tt, .q__copy, .note { display: none !important; }

  .page { width: auto; max-width: none; margin: 0; padding: 0; }
  .hd { padding-bottom: 3mm; margin-bottom: 5mm; }
  .name { font-size: 20pt; }
  .role { font-size: 10pt; }
  .grid { row-gap: 6mm; }
  /* На бумаге полоса справочных разделов фиксированная в три колонки:
     auto-fit в печати считает ширину страницы иначе и частенько даёт
     одну колонку, из-за чего резюме расползается на лишнюю страницу. */
  .col-rail { grid-template-columns: repeat(3, 1fr); column-gap: 6mm;
              border-top: 0.5pt solid #d8d5cf; padding-top: 4mm; }
  .sec { margin-bottom: 5mm; break-inside: avoid; }
  .job { padding-block: 2mm; break-inside: avoid; }
  .h { margin-bottom: 3mm; }
  .tbl { font-size: 8.5pt; }
  .bul { gap: 2mm; }
  .ft { font-size: 7.5pt; margin-top: 5mm; }

  /* На бумаге href не виден, поэтому ссылка раскрывается текстом. */
  a { color: #14130f !important; }
  a[href^="http"]::after {
    content: " (" attr(href) ")";
    font-size: 7pt;
    color: #5c5952;
    word-break: break-all;
  }
}
"""

NO_FLASH_JS = """
/* Тема выставляется до первой отрисовки: иначе страница успевает
   показаться тёмной и только потом перекрашивается. */
(function () {
  try {
    var v = localStorage.getItem("pf-theme");
    document.documentElement.setAttribute(
      "data-theme",
      ["system", "light", "dark"].indexOf(v) === -1 ? "system" : v
    );
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "system");
  }
})();
"""

ENGINE_JS = """
(function () {
  "use strict";
  var KEY = "pf-theme";
  var ORDER = ["system", "light", "dark"];
  var LABELS = { system: "Тема: как в системе", light: "Тема: светлая", dark: "Тема: тёмная" };
  var SHORT = { system: "Авто", light: "Светлая", dark: "Тёмная" };

  function read() {
    try {
      var v = localStorage.getItem(KEY);
      return ORDER.indexOf(v) === -1 ? "system" : v;
    } catch (e) { return "system"; }
  }
  function save(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  var current = read();

  function sync(btn) {
    var label = btn.querySelector("[data-theme-label]");
    if (label) label.textContent = SHORT[current];
    btn.setAttribute("aria-label", LABELS[current]);
    btn.setAttribute("title", LABELS[current] + " — нажмите, чтобы сменить");
  }

  var btn = document.querySelector("[data-theme-toggle]");
  if (btn) {
    sync(btn);
    btn.addEventListener("click", function () {
      current = ORDER[(ORDER.indexOf(current) + 1) % ORDER.length];
      document.documentElement.setAttribute("data-theme", current);
      save(current);
      sync(btn);
    });
  }

  /* Копирование блока сообщения: шпаргалкой пользуются так — скопировал
     и вставил в Telegram. Кнопка экономит ровно это действие. */
  document.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var src = b.closest(".q").querySelector("[data-copy-src]");
      if (!src) return;
      var text = src.innerText.trim();
      navigator.clipboard.writeText(text).then(function () {
        var old = b.textContent;
        b.textContent = "Скопировано";
        b.classList.add("is-ok");
        setTimeout(function () { b.textContent = old; b.classList.remove("is-ok"); }, 1400);
      });
    });
  });
})();
"""


def contact_item(chunk: str) -> str:
    """Элемент контакта: почта, телефон, Telegram, сайт."""
    text = chunk.strip()
    if "@" in text and not text.startswith("@"):
        return f'<li><a href="mailto:{html.escape(text, quote=True)}">{html.escape(text)}</a></li>'
    if text.startswith("+"):
        # Телефон в href пишется через дефис: сплошная последовательность
        # цифр срезается фильтром секретов при публикации.
        #
        # Квантификатор `+` обязателен. Без него каждый нецифровой символ
        # заменялся своим дефисом: `+7 (925) 888-58-82` давал
        # `+7--925--888-58-82` — ссылка собиралась, но не звонила.
        # Проверялось запуском: во всех пяти HTML до правки стоял
        # именно такой href со сдвоенными дефисами.
        digits = re.sub(r"[^\d+]+", "-", text)
        return f'<li><a href="tel:{html.escape(digits, quote=True)}">{html.escape(text)}</a></li>'
    if text.startswith("@"):
        # В исходнике контакт записан как `@eandreev (t.me/eandreev)`:
        # ник и пояснение, где он живёт. В href уходит только ник —
        # иначе собиралось `https://t.me/eandreev (t.me/eandreev)`,
        # ссылка с пробелом и скобками, которая не открывается.
        nick = re.split(r"[\s(]", text.lstrip("@"), maxsplit=1)[0]
        return f'<li><a href="https://t.me/{html.escape(nick, quote=True)}">{html.escape(text)}</a></li>'
    match = BARE_URL.match(text)
    if match:
        return f'<li><a href="https://{html.escape(match.group(1), quote=True)}">{html.escape(text)}</a></li>'
    return f"<li>{html.escape(text)}</li>"


def render_blocks(blocks: list, in_job: bool = False) -> str:
    """Блоки секции в HTML.

    Параграф, начинающийся с жирного и содержащий « · » — это строка
    опыта, а не абзац. Она уходит в сетку с отдельным столбцом дат.
    """
    out: list[str] = []
    pending: list[tuple[str, str]] = []

    def flush_jobs() -> None:
        if not pending:
            return
        out.append('<div class="jobs">')
        for when, place, role, body in pending:
            out.append('<article class="job">')
            out.append(f'<div class="job__when">{html.escape(when)}</div>')
            out.append('<div class="job__what">')
            out.append(f"<h3>{inline(place)}</h3>")
            if role:
                out.append(f'<p class="job__role">{inline(role)}</p>')
            for line in body:
                out.append(f"<p>{inline(line)}</p>")
            out.append("</div></article>")
        out.append("</div>")
        pending.clear()

    for kind, payload in blocks:
        if kind == "table":
            flush_jobs()
            rows = [r for r in payload if not re.match(r"^\|[\s:|-]+\|$", r.strip())]
            out.append('<div class="tbl-wrap"><table class="tbl">')
            for index, row in enumerate(rows):
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                tag = "th" if index == 0 else "td"
                out.append("<tr>" + "".join(f"<{tag}>{linkify(c)}</{tag}>" for c in cells) + "</tr>")
            out.append("</table></div>")
        elif kind == "ul":
            flush_jobs()
            out.append('<ul class="bul">' + "".join(f"<li>{inline(i)}</li>" for i in payload) + "</ul>")
        elif kind == "quote":
            flush_jobs()
            body = "".join(f"<p>{inline(i)}</p>" for i in payload)
            out.append(
                '<blockquote class="q"><div data-copy-src>' + body + "</div>"
                '<button class="q__copy" type="button" data-copy>Скопировать</button></blockquote>'
            )
        else:
            text = payload.strip()
            head, rest = split_bold_span(text)
            if head and " · " in head:
                # Всё, что стоит после закрывающей «**», — описание, а не
                # название. Парсер склеил его с заголовком в один абзац
                # (в markdown это соседние строки), поэтому здесь оно
                # возвращается обратно в тело, иначе уезжает в <h3>.
                when, place, role = split_job(head)
                pending.append((when, place, role, [rest] if rest else []))
                continue
            if pending:
                pending[-1][3].append(text)
                continue
            # Курсивная строка сразу после заголовка — служебная инструкция,
            # а не содержание: читателю её показывать не надо.
            if text.startswith("*") and text.endswith("*") and not text.startswith("**"):
                out.append(f'<div class="note">{inline(text.strip("*"))}</div>')
            else:
                out.append(f'<p class="txt">{inline(text)}</p>')

    flush_jobs()
    return "\n".join(out)


def render(doc: dict, source: Path, playbook: bool) -> str:
    """Собирает страницу целиком."""
    role = doc["h1"]
    name = doc["h2"] or "Евгений Андреев"
    title = f"{name} — {role}" if doc["h2"] else role

    contacts = "".join(contact_item(c) for c in doc["contacts"].split("·")) if doc["contacts"] else ""

    header = ""
    if contacts or doc["h2"]:
        meta = doc["h2"].split(" · ", 1)[1] if " · " in doc["h2"] else ""
        header = f"""
  <header class="hd">
    <div>
      <h1 class="name">{html.escape(name.split(" · ")[0])}</h1>
      <p class="role">{inline(role)}</p>
      {f'<p class="meta">{html.escape(meta)}</p>' if meta else ""}
    </div>
    <ul class="ct">{contacts}</ul>
  </header>"""

    # Текст до первого раздела. Курсивный — служебная инструкция себе,
    # читателю её показывать не надо; обычный — вступление, его надо.
    lead_parts = []
    for part in doc["lead"]:
        if part.startswith("*") and part.endswith("*"):
            lead_parts.append(f'<div class="note">{inline(part.strip("*"))}</div>')
        else:
            lead_parts.append(f'<p class="lead-p">{inline(part)}</p>')
    lead = "".join(lead_parts)

    main_col, rail_col, wide_col = [], [], []
    for section in doc["sections"]:
        block = f'<section class="sec"><h2 class="h">{html.escape(section["title"])}</h2>' + render_blocks(
            section["blocks"]
        ) + "</section>"
        if section["title"] in RAIL_SECTIONS:
            rail_col.append(block)
        elif section["title"] in WIDE_SECTIONS:
            wide_col.append(block)
        else:
            main_col.append(block)

    grid = ""
    if playbook:
        grid = '<main class="grid"><div class="col-main">' + "\n".join(main_col + wide_col + rail_col) + "</div></main>"
    else:
        # Порядок чтения: кто я → чем подтверждено (артефакты) →
        # справка (инструменты, образование, условия). Раньше справка
        # шла сразу за основной колонкой и отрывала артефакты от
        # рассказа: ссылки на репозитории оказывались в самом низу,
        # после разговора про деньги.
        grid = f"""
  <main class="grid">
    <div class="col-main">{"".join(main_col)}</div>
    <div class="col-wide">{"".join(wide_col)}</div>
    <aside class="col-rail">{"".join(rail_col)}</aside>
  </main>"""

    return f"""<!doctype html>
<html lang="ru" data-theme="system">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(role)}. Евгений Андреев: 28 лет в системах с высокой ценой ошибки — промышленная автоматизация, сервис для UHNWI, сейчас Python и языковые модели в продакшене.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600&family=Oswald:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
{TOKENS_DARK}
html[data-theme="light"] {{ {TOKENS_LIGHT} }}
@media (prefers-color-scheme: light) {{
  html[data-theme="system"] {{ {TOKENS_LIGHT} }}
}}
{CSS}
</style>
<script>{NO_FLASH_JS}</script>
</head>
<body>
<button class="tt" type="button" data-theme-toggle aria-label="Тема: как в системе">
  <span class="tt__i" aria-hidden="true"></span><span data-theme-label>Авто</span>
</button>
<div class="page">
{header}{lead}{grid}
  <footer class="ft">{inline(doc["footer"]) if doc["footer"] else f"Собрано из {source.name} — факты не меняются между версиями под роли."}</footer>
</div>
<script>{ENGINE_JS}</script>
</body>
</html>
"""


def main() -> int:
    if not SRC.is_dir():
        print(f"Нет каталога {SRC}")
        return 1

    built = []
    for md_path in sorted(SRC.glob("*.md")):
        doc = parse(md_path.read_text(encoding="utf-8"))
        # Шпаргалка отличается устройством: в ней нет имени и контактов
        # в шапке, а секции идут вторым уровнем. Её не отправляют
        # работодателю, поэтому и подача другая — один столбец.
        playbook = not doc["h2"]
        out = render(doc, md_path, playbook)
        html_path = md_path.with_suffix(".html")
        html_path.write_text(out, encoding="utf-8")
        built.append((html_path.name, "шпаргалка" if playbook else "резюме", len(out)))

    for name, kind, size in built:
        print(f"  ✓ {name:<24} {kind:<10} {size:>6} байт")
    print(f"\nСобрано файлов: {len(built)}. Факты правятся в RESUME_MASTER.md, затем здесь перезапуск.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
