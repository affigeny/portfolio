#!/usr/bin/env python3
"""Считает контраст текста и фона по WCAG 2.1.

Зачем скрипт, если контраст видно глазом
----------------------------------------
Не видно. Глаз приспосабливается: серый на белом кажется читаемым,
пока не посчитать. А «читается нормально» — это не критерий, потому что
у читателя могут быть другие монитор, освещение и зрение.

Поэтому каждый раз, когда меняется палитра, прогоняется эта проверка.
Она не про эстетику, она про то, что текст обязан быть прочитан.

Пороги WCAG 2.1
---------------
  AA  — 4.5:1 для обычного текста, 3:1 для крупного (≥ 18.66px жирным
        или ≥ 24px обычным);
  AAA — 7:1 для обычного текста, 4.5:1 для крупного.

Почему здесь разбирается oklch
------------------------------
Палитра описывает акцент формулой, а не константой:
`oklch(var(--metal-l) var(--metal-c) var(--metal-h))`. Пока скрипт умел
читать только шестнадцатеричные значения, акцент выпадал из проверки
молча: строк с «#» в файле не находится, пар не считается, на выходе
бодрое «все пары в норме», которого не добирается половина. Это худший
вид проверки — та, что подтверждает отсутствие проблем, потому что не
смотрит.

Поэтому теперь разбираются hex, rgb/rgba, oklch, вложенные var() и
простые calc() вида «a + b». Прозрачность не игнорируется, а
композитится над фоном пары: `--accent-soft` поверх `--surface`
считается честно, а не как непрозрачный цвет.

Проверка идёт по декартову произведению: файл × тема × металл. Металл
меняет акцент, значит, и контраст надо проверять для каждого из трёх,
а не для латуни, которая стоит по умолчанию.

Запуск
------
    python3 _check_contrast.py          # сводка и все провалы
    python3 _check_contrast.py -v       # все пары построчно

Выход: сводка по файлу и теме, подробно — только провалы.
Код возврата 1, если хоть одна пара не проходит AA.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Пары, которые реально встречаются в вёрстке: текст на подложке.
# Проверять все сочетания бессмысленно — они не используются вместе.
PAIRS = [
    ("--text", "--bg", 7.0),
    ("--text", "--surface", 7.0),
    ("--muted", "--bg", 4.5),
    ("--muted", "--surface", 4.5),
    ("--dim", "--bg", 4.5),
    ("--dim", "--surface", 4.5),
    ("--accent", "--bg", 4.5),
    ("--accent", "--surface", 4.5),
    # Уровни критичности: цвет здесь несёт смысл, а не украшение. Если
    # уровень неразличим по контрасту, он перестаёт работать.
    ("--crit", "--surface", 4.5),
    ("--high", "--surface", 4.5),
    ("--med", "--surface", 4.5),
    ("--low", "--surface", 4.5),
]

# Металлы в том же порядке, что в assets/theme.js. Порядок важен только
# для отчёта: первый — значение по умолчанию.
METALS = ["brass", "bronze", "copper"]


# ── Цвет: разбор ──────────────────────────────────────────────────────


def srgb_to_linear(channel: float) -> float:
    """sRGB-канал 0..1 в линейное значение 0..1."""
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def oklch_to_linear(light: float, chroma: float, hue: float) -> tuple[float, float, float]:
    """Oklch в линейный sRGB.

    Формулы Björn Ottosson, те же, что применяет браузер. Без этого
    перехода акцент, записанный как oklch, проверить нельзя вовсе.
    """
    a = chroma * math.cos(math.radians(hue))
    b = chroma * math.sin(math.radians(hue))

    l_ = light + 0.3963377774 * a + 0.2158037573 * b
    m_ = light - 0.1055613458 * a - 0.0638541728 * b
    s_ = light - 0.0894841775 * a - 1.2914855480 * b

    l, m, s = l_**3, m_**3, s_**3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*?))?\s*\)")
CALC_RE = re.compile(r"calc\(([^()]*)\)")


def eval_calc(text: str) -> str:
    """Считает calc() вида «a + b» и «a − b».

    Полный арифметический разбор здесь не нужен: в палитре ровно один
    calc — сдвиг светлоты к состоянию :hover. А вот без него
    `--accent-hover` остался бы непрозрачной строкой и выпал бы из
    проверки так же, как раньше выпадал сам акцент.
    """
    previous = None
    while previous != text:

        def replace(match: re.Match) -> str:
            tokens = match.group(1).split()
            number = r"^-?\d*\.?\d+$"
            if (
                len(tokens) == 3
                and re.match(number, tokens[0])
                and tokens[1] in "+-"
                and re.match(number, tokens[2])
            ):
                left, op, right = float(tokens[0]), tokens[1], float(tokens[2])
                return f"{left + right if op == '+' else left - right:g}"
            return match.group(0)

        previous = text
        text = CALC_RE.sub(replace, text)
    return text


def resolve(value: str, palette: dict[str, str], depth: int = 0) -> str:
    """Подставляет var() и считает calc() до получения строки с числами."""
    if depth > 10:
        return value

    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name in palette:
            return resolve(palette[name], palette, depth + 1)
        fallback = match.group(2)
        return resolve(fallback, palette, depth + 1) if fallback else ""

    return eval_calc(VAR_RE.sub(replace, value).strip())


def to_linear(value: str, palette: dict[str, str]) -> tuple[float, float, float, float] | None:
    """Любое значение CSS-цвета в линейный sRGB плюс альфа.

    Возвращает None, если цвет разобрать нельзя. Такое значение
    пропускается, но попадает в счётчик неразобранного — чтобы молчаливая
    дыра в проверке была видна, а не пряталась среди успешных пар.
    """
    text = resolve(value, palette).strip()

    if text.startswith("#"):
        raw = text.lstrip("#")
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        if len(raw) >= 6:
            channels = [int(raw[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
            alpha = int(raw[6:8], 16) / 255.0 if len(raw) >= 8 else 1.0
            return (*(srgb_to_linear(c) for c in channels), alpha)

    if text.startswith("rgb"):
        numbers = re.findall(r"-?\d*\.?\d+%?", text)
        if len(numbers) >= 3:
            channels = [
                float(n.rstrip("%")) / 100.0 if n.endswith("%") else float(n) / 255.0
                for n in numbers[:3]
            ]
            alpha = 1.0
            if len(numbers) >= 4:
                alpha = float(numbers[3].rstrip("%")) / (
                    100.0 if numbers[3].endswith("%") else 1.0
                )
            return (*(srgb_to_linear(c) for c in channels), alpha)

    if text.startswith("oklch") or text.startswith("oklab"):
        body = text[text.index("(") + 1 : text.rindex(")")]
        parts, alpha = body.split("/", 1) if "/" in body else (body, "")
        numbers = re.findall(r"-?\d*\.?\d+%?", parts)
        if len(numbers) >= 3:
            light = float(numbers[0].rstrip("%")) / (
                100.0 if numbers[0].endswith("%") else 1.0
            )
            # Насыщенность в процентах отсчитывается от 0.4 — так в CSS,
            # и отличие от светлоты здесь принципиальное.
            chroma = float(numbers[1].rstrip("%")) / (
                2.5 if numbers[1].endswith("%") else 1.0
            )
            hue = float(numbers[2].rstrip("deg"))
            a = 1.0
            if alpha:
                found = re.search(r"-?\d*\.?\d+%?", alpha)
                if found:
                    token = found.group(0)
                    a = float(token.rstrip("%")) / (100.0 if token.endswith("%") else 1.0)
            return (*oklch_to_linear(light, chroma, hue), a)

    return None


# ── Контраст ──────────────────────────────────────────────────────────


def composite(fg: tuple[float, float, float, float], bg: tuple[float, float, float]) -> tuple:
    """Накладывает полупрозрачный цвет на непрозрачный фон.

    Прозрачность без этого давала бы ложный результат: `--accent-soft`
    считался бы как плотный цвет и либо проходил, либо нет — в обоих
    случаях не про то, что видит читатель.
    """
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1.0 - a) for i in range(3))


def luminance(rgb: tuple[float, float, float]) -> float:
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def contrast(
    fg: tuple[float, float, float, float], bg: tuple[float, float, float, float]
) -> float:
    """Контраст двух цветов, большее отношение к меньшему."""
    bgc = (bg[0], bg[1], bg[2])
    l1 = luminance(composite(fg, bgc))
    l2 = luminance(bgc)
    lo, hi = min(l1, l2), max(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


# ── Разбор CSS ────────────────────────────────────────────────────────


def iter_blocks(text: str, start: int = 0, end: int | None = None):
    """Все блоки `селекторы { объявления }`, включая вложенные.

    Возвращает пары (список селекторов, тело).

    Почему рекурсия, а не линейное сканирование со сдвигом на один
    символ. Прежняя версия шла по строке подряд и брала селектором всё
    от предыдущей открывающей скобки — то есть в селектор попадал хвост
    предыдущего блока вместе с его закрывающей `}`. Срабатывало только
    там, где перед `{` случайно не было текста: `html[data-theme="system"]`
    внутри @media находился, а `html[data-theme="light"]` снаружи — нет.

    Проверка от этого не падала, а молча сужалась: палитра металлов,
    целиком лежащая внутри @supports, не проверялась вообще, а сводка
    всё равно сообщала «все пары в норме».

    Теперь at-правила (@media, @supports) раскрываются: их тело
    разбирается отдельным проходом, поэтому селектор внутри получается
    чистым.
    """
    i = start
    n = len(text) if end is None else end
    while i < n:
        if text[i] == "{":
            selector = text[start:i].strip()
            depth, j = 1, i + 1
            while j < n and depth:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
            # Границы тела запоминаются до сдвига указателя: иначе
            # рекурсия получает пустой диапазон и вложенные блоки
            # пропадают — а вместе с ними и всё, что лежит внутри
            # @supports, включая палитру металлов.
            body_start, body_end = i + 1, j - 1
            i = j
            start = j
            if selector.startswith("@"):
                # Печать пропускается целиком. В ней свой `:root` с
                # приглушённым акцентом, и стоит он последним в файле:
                # без этого исключения он перекрывал бы рабочую формулу
                # акцента, и проверка считала бы контраст печати как
                # контраст экрана.
                if re.search(r"\bprint\b", selector):
                    continue
                # У at-правила нет объявлений — есть вложенные блоки.
                yield from iter_blocks(text, body_start, body_end)
            else:
                yield selector, text[body_start:body_end]
        else:
            i += 1


def extract_block(text: str, selector: str) -> dict[str, str]:
    """Объявления `--name: значение;` из блоков, где есть нужный селектор.

    Селектор ищется среди частей списка через запятую: палитра записана
    как `:root, html[data-theme="dark"] { ... }`, и поиск точного
    вхождения `:root {` такой блок не найдёт — скрипт молча не увидел
    бы ни одного цвета и честно рапортовал бы об отсутствии проблем.

    Значение берётся любое, а не только шестнадцатеричное: разбор цвета
    происходит позже, в to_linear.
    """
    found: dict[str, str] = {}
    wanted = selector.strip()
    for selectors, body in iter_blocks(text):
        parts = [p.strip() for p in selectors.split(",")]
        if wanted not in parts:
            continue
        for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+)\s*;", body):
            found[name] = value.strip()
    return found


# ── Отчёт ─────────────────────────────────────────────────────────────


def main() -> int:
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    targets = [ROOT / "assets" / "design.css"] + sorted(ROOT.glob("resumes/*.html"))
    failures: list[str] = []
    unparsed: list[str] = []
    total = 0
    worst: dict[tuple[str, str], tuple[float, str]] = {}

    for path in targets:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        text_nc = re.sub(r"/\*.*?\*/", "", text, flags=re.S)

        # Палитры собираются так же, как их видит браузер: :root — базис,
        # тема — переопределения. Иначе светлая тема остаётся без тех
        # свойств, которые в её блоке не объявлены.
        #
        # Это не теоретическая аккуратность. Формула акцента записана
        # ровно один раз, в :root внутри @supports. Блок светлой темы
        # объявляет только светлоту металла, а сам --accent наследует.
        # Пока светлая палитра собиралась из одного своего блока, туда
        # попадал старый шестнадцатеричный акцент, и все три металла
        # давали один и тот же результат — проверка выглядела рабочей,
        # но считала не то.
        # Каскад воспроизводится упрощённо, но в том же порядке, что и в
        # браузере: :root → правило с конкретной темой → правило без
        # уточнения темы (`html[data-theme]`).
        #
        # Последняя ступень не формальность. Акцент записан селектором
        # `html[data-theme]`, потому что `:root` проигрывает темам по
        # специфичности. Проверка, которая не знает этой ступени,
        # посчитает контраст старого шестнадцатеричного акцента и не
        # заметит подмены.
        base = extract_block(text_nc, ":root")
        generic = extract_block(text_nc, "html[data-theme]")

        dark = dict(base)
        dark.update(extract_block(text_nc, 'html[data-theme="dark"]'))
        dark.update(generic)

        light = dict(base)
        light.update(extract_block(text_nc, 'html[data-theme="light"]'))
        light.update(extract_block(text_nc, 'html[data-theme="system"]'))
        light.update(generic)

        # Металлы есть не везде: страницы резюме самодостаточны и живут
        # на своей палитре. Там проверяется один проход без металла.
        #
        # Латунь проверяется наравне с остальными, хотя отдельного блока
        # под неё нет: это значение по умолчанию, записанное в :root.
        # Брать список металлов из найденных блоков нельзя — латунь из
        # такого списка выпала бы, и акцент по умолчанию оказался бы
        # единственным, который никто не проверил.
        metal_overrides = {
            m: extract_block(text_nc, f'html[data-metal="{m}"]') for m in METALS
        }
        metals = METALS if any(metal_overrides.values()) else [None]

        for theme_name, palette in (("тёмная", dark), ("светлая", light)):
            if not palette:
                continue
            for metal in metals:
                forced = dict(palette)
                if metal:
                    forced.update(metal_overrides[metal])

                for fg_name, bg_name, need in PAIRS:
                    if fg_name not in forced or bg_name not in forced:
                        continue
                    fg = to_linear(forced[fg_name], forced)
                    bg = to_linear(forced[bg_name], forced)
                    if fg is None:
                        unparsed.append(f"{path.name} · {theme_name} · {fg_name}")
                        continue
                    if bg is None:
                        unparsed.append(f"{path.name} · {theme_name} · {bg_name}")
                        continue

                    ratio = contrast(fg, bg)
                    total += 1
                    ok = ratio >= need
                    label = f"{path.name} · {theme_name}"
                    if metal:
                        label += f" · {metal}"
                    pair = f"{fg_name} → {bg_name}"

                    if not ok:
                        failures.append(
                            f"  ПЛОХО {label:<38} {pair:<26} "
                            f"{ratio:6.2f}:1  (нужно {need})"
                        )
                    if verbose:
                        print(
                            f"  {'ok  ' if ok else 'ПЛОХО'} {label:<38} {pair:<26} "
                            f"{ratio:6.2f}:1  (нужно {need})"
                        )

                    key = (path.name, theme_name if not metal else f"{theme_name}/{metal}")
                    known = worst.get(key)
                    headroom = ratio / need
                    if known is None or headroom < known[0]:
                        worst[key] = (headroom, f"{ratio:.2f}:1  {pair}")

    if not total:
        print("Не нашёл ни одной пары — проверь, что файлы на месте.")
        return 1

    print()
    for (name, theme), (headroom, note) in sorted(worst.items()):
        print(f"  {name:<24} {theme:<18} худшая пара: {note}")

    if unparsed:
        print(f"\n  ! Не разобрано значений: {len(unparsed)}")
        for item in unparsed[:10]:
            print(f"      {item}")
        if len(unparsed) > 10:
            print(f"      … и ещё {len(unparsed) - 10}")

    print()
    if failures:
        print(f"✗ Не проходят порог: {len(failures)} пар из {total}.")
        for line in failures:
            print(line)
        return 1

    print(f"✓ Все {total} пар проходят порог.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
