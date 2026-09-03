#!/usr/bin/env python3
"""Ставит на все страницы портфолио единый переключатель тем.

Зачем отдельный скрипт, а не правка руками
------------------------------------------
Страницы писались в разное время и живут на четырёх разных наборах
CSS-переменных: `--ink/--surface/--fire` в index и value, `--ink2/--surface2`
в models и sorterlab, `--bg/--card/--border` в archetypes и writing,
плюс у каждой страницы десятки цветов, прописанных прямо в правилах
(`#0A0500`, `oklch(5% 0 0/.72)`). Переменные потрогать легко — хардкод
в правилах уже нет. Поэтому светлая палитра считается автоматически:

    светлый цвет = тот же тон и та же прозрачность, светлота зеркально
    перевёрнута (L -> 100 - L)

Так `oklch(5% 0 0/.72)` становится `oklch(95% 0 0/.72)`, а оранжевый
акцент `oklch(70% .19 48)` — приглушённым `oklch(30% .19 48)`, который
читается на светлом фоне. Оттенок и альфа сохраняются, фотографии и
svg-иконки не затрагиваются — в отличие от `filter: invert(1)` на весь
документ, который перекрашивает картинки.

Что делает скрипт
-----------------
1. Читает `:root` страницы, достаёт оттуда цвета и строит зеркальную
   светлую версию каждой переменной.
2. Проходит по остальным правилам и находит цвета, прописанные прямо
   в них. Тёмные фоны и границы переворачивает в светлые, светлый текст —
   в тёмный. Правила с псевдоклассами (`:hover`) пропускает, иначе
   переопределение перебьёт ховер и ссылки перестанут отзываться.
3. Кладет результат в конец `<style>` — после авторских правил, чтобы
   переопределение выигрывало по порядку.
4. В `<head>` ставит скрипт, который выставляет тему до первой
   отрисовки: без него страница мигает тёмной перед светлой.
5. Добавляет кнопку переключения — одна и та же на всех страницах.

Тема по умолчанию — системная. Выбор пользователя запоминается в
localStorage и имеет приоритет над системной настройкой.

Запуск
------
    python3 _apply_theme.py

Скрипт идемпотентен: повторный запуск не дублирует код, а перезаписывает
блок, помеченный маркером ENGINE_MARKER.
"""

import colorsys
import pathlib
import re

BASE = pathlib.Path(__file__).parent.parent
ENGINE_MARKER = "theme-engine-v1"
STORAGE_KEY = "pf-theme"

# Страницы, которые не публикуются и в общий обход не идут.
SKIP_PREFIX = ("proto_", "prototype_", "index_photo")

# ── Имена переменных по роли ────────────────────────────────────────
# От роли зависит, в какой диапазон светлоты попадёт зеркальный цвет:
# фон должен стать светлым, текст — тёмным, акцент — остаться ярким.
SURFACE_HINTS = ("bg", "ink", "surface", "card", "line", "border", "ground")
TEXT_HINTS = ("text", "fg", "muted", "dim", "subtle", "label")

# ── Свойства, значения которых переворачиваются ─────────────────────
SURFACE_PROPS = {
    "background", "background-color", "background-image",
    "border", "border-color",
    "border-top", "border-right", "border-bottom", "border-left",
    "border-top-color", "border-right-color",
    "border-bottom-color", "border-left-color",
    "box-shadow", "outline", "outline-color",
}
TEXT_PROPS = {"color", "-webkit-text-fill-color", "caret-color",
              "text-decoration-color", "column-rule-color"}

# ── Поиск цветов в CSS ──────────────────────────────────────────────
# Порядок важен: oklch ищется первым, потому что внутри могут быть
# проценты и дроби, которые confuse-ят более простые шаблоны.
COLOR_RE = re.compile(
    r"oklch\(\s*(?P<l>[\d.]+)%\s+(?P<c>[\d.]+)\s+(?P<h>[\d.]+)"
    r"(?:\s*/\s*(?P<a>[\d.]+%?))?\s*\)"
    r"|hsl\(\s*(?P<hh>[\d.]+)[,\s]+(?P<hs>[\d.]+)%\s*[,\s]+(?P<hl>[\d.]+)%"
    r"(?:\s*/\s*(?P<ha>[\d.]+%?))?\s*\)"
    r"|rgba?\(\s*(?P<r>[\d.]+)[,\s]+(?P<g>[\d.]+)[,\s]+(?P<b>[\d.]+)"
    r"(?:\s*[,\s/]\s*(?P<ra>[\d.]+%?))?\s*\)"
    r"|(?P<hex>#[0-9a-fA-F]{3,8})\b",
    re.IGNORECASE,
)


# ── Разбор и сборка цвета ───────────────────────────────────────────

class Color:
    """Цвет в одной из трёх форм: oklch, hsl или hex.

    Держим исходную форму, чтобы не перекрашивать без нужды: значение
    в oklch так и вернётся в oklch, а hex — в hex.
    """

    def __init__(self, kind, parts, alpha=None):
        self.kind = kind          # "oklch" | "hsl" | "hex"
        self.parts = parts        # кортеж числовых компонент
        self.alpha = alpha        # строка как в исходнике или None

    @property
    def lightness(self):
        """Светлота в процентах — общая шкала для всех форм."""
        if self.kind == "oklch":
            return self.parts[0]
        if self.kind == "hsl":
            return self.parts[2]
        r, g, b = self.parts
        return colorsys.rgb_to_hls(r / 255, g / 255, b / 255)[1] * 100

    def flipped(self, low, high):
        """Зеркальный цвет: тон и альфа те же, светлота перевёрнута.

        low и high — границы, в которые жмётся результат. Для фонов это
        почти белый, для текста — почти чёрный, для акцентов — середина.
        """
        new_l = min(max(100.0 - self.lightness, low), high)

        if self.kind == "oklch":
            l, c, h = self.parts
            out = f"oklch({_num(new_l)}% {_num(c)} {_num(h)}"
        elif self.kind == "hsl":
            h, s, _ = self.parts
            out = f"hsl({_num(h)} {_num(s)}% {_num(new_l)}%"
        else:
            r, g, b = self.parts
            hh, ll, ss = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            rr, gg, bb = colorsys.hls_to_rgb(hh, new_l / 100, ss)
            out = "#%02x%02x%02x" % tuple(round(v * 255) for v in (rr, gg, bb))

        if self.alpha:
            out += f" / {self.alpha}"
        return out + ")"


def _num(v):
    """Печатает число без лишних нулей: 30.0 -> 30, 47.62 -> 47.62."""
    return str(int(v)) if float(v).is_integer() else f"{v:.4g}"


def parse_color(text):
    """Достаёт из строки первый цвет и возвращает (Color, span)."""
    m = COLOR_RE.search(text)
    if not m:
        return None, None
    g = m.groupdict()

    if g["l"] is not None:
        return Color("oklch", (float(g["l"]), float(g["c"]), float(g["h"])),
                     g["a"]), m.span()
    if g["hl"] is not None:
        return Color("hsl", (float(g["hh"]), float(g["hs"]), float(g["hl"])),
                     g["ha"]), m.span()
    if g["r"] is not None:
        return Color("hex", (float(g["r"]), float(g["g"]), float(g["b"])),
                     g["ra"]), m.span()

    raw = g["hex"][1:]
    if len(raw) in (3, 4):
        raw = "".join(ch * 2 for ch in raw)
    r, gg, b = (int(raw[i:i + 2], 16) for i in (0, 2, 4))
    alpha = None
    if len(raw) == 8:
        alpha = _num(round(int(raw[6:8], 16) / 255 * 100) / 100)
    return Color("hex", (r, gg, b), alpha), m.span()


def recolor(value, prop):
    """Перекрашивает все цвета в значении свойства.

    Возвращает None, если перекрашивать нечего — тогда правило в
    светлую тему не попадёт, что экономит размер и не портит ховеры.
    """
    if prop in TEXT_PROPS:
        low, high = 12.0, 42.0          # текст: тёмный на светлом
    elif prop in SURFACE_PROPS:
        low, high = 84.0, 98.0          # фон и границы: светлые
    else:
        return None

    out, pos, changed = value, 0, False
    while True:
        color, span = parse_color(out[pos:])
        if not color:
            break
        start, end = pos + span[0], pos + span[1]
        out = out[:start] + color.flipped(low, high) + out[end:]
        pos = start + len(color.flipped(low, high))
        changed = True
    return out if changed else None


def flip_variable(name, value):
    """Зеркалит цвет CSS-переменной с учётом её роли по имени."""
    color, span = parse_color(value)
    if not color:
        return None
    lowered = name.lower()
    if any(h in lowered for h in TEXT_HINTS):
        low, high = 10.0, 45.0
    elif any(h in lowered for h in SURFACE_HINTS):
        low, high = 4.0, 96.0
    else:
        low, high = 34.0, 66.0          # акцент остаётся акцентом
    flipped = color.flipped(low, high)
    start, end = span
    return value[:start] + flipped + value[end:]


# ── Разбор CSS на правила ───────────────────────────────────────────

RULE_RE = re.compile(r"(?P<sel>[^{}@]+?)\s*\{\s*(?P<body>[^{}]*?)\s*\}",
                     re.S)
PSEUDO_CLASS_RE = re.compile(r":[a-z-]+", re.IGNORECASE)


def build_light_css(css):
    """Собирает светлую палитру для одной страницы: переменные + хардкод."""
    var_lines, hard_rules = [], []

    for m in RULE_RE.finditer(css):
        selector, body = m.group("sel").strip(), m.group("body")

        # :root — это палитра страницы, её зеркалим по именам переменных
        if selector == ":root" or selector.startswith(":root"):
            for decl in body.split(";"):
                if ":" not in decl:
                    continue
                name, _, value = decl.partition(":")
                name, value = name.strip(), value.strip()
                if not name.startswith("--"):
                    continue
                flipped = flip_variable(name, value)
                if flipped and flipped != value:
                    var_lines.append(f"  {name}:{flipped}")
            continue

        if not selector or selector.startswith("@"):
            continue
        # Правила с псевдоклассами не трогаем: переопределение окажется
        # специфичнее ховера и ссылки перестанут реагировать на мышь.
        if PSEUDO_CLASS_RE.search(selector):
            continue
        # Чужие движки (например, собственный переключатель темы на
        # странице) не перекрашиваем — у них своя палитра.
        if "data-theme" in selector:
            continue

        flipped_decls = []
        for decl in body.split(";"):
            if ":" not in decl:
                continue
            prop, _, value = decl.partition(":")
            prop, value = prop.strip().lower(), value.strip()
            if prop.startswith("--") or "var(" in value:
                continue
            new_value = recolor(value, prop)
            if new_value:
                flipped_decls.append(f"{prop}:{new_value}")

        if flipped_decls:
            hard_rules.append(
                f"html[data-theme=\"light\"] {selector}"
                f"{{{';'.join(flipped_decls)}}}"
            )

    return var_lines, hard_rules


# ── Внедряемые блоки ────────────────────────────────────────────────

NO_FLASH_JS = f"""<script>
/* Тема выставляется до первой отрисовки: иначе страница на мгновение
   показывается системной, а потом перекрашивается — это заметно глазом.
   Приоритет: выбор пользователя в localStorage -> системная настройка. */
(function(){{
  var KEY='{STORAGE_KEY}';
  var saved=null; try{{saved=localStorage.getItem(KEY)}}catch(e){{}}
  var systemDark=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;
  var theme=(saved==='light'||saved==='dark')?saved:(systemDark?'dark':'light');
  document.documentElement.setAttribute('data-theme',theme);
}})();
</script>"""

ENGINE_CSS = """
/* ══ ДВИЖОК ТЕМЫ · ставится _apply_theme.py, не править руками ══
   Светлая палитра посчитана автоматически: тот же тон и прозрачность,
   светлота зеркально перевёрнута. Тёмная — авторская, не трогается.
   color-scheme нужен, чтобы нативные элементы (скроллбар, поля ввода,
   автофил) подстраивались под тему вместе со страницей. */
html[data-theme="light"]{color-scheme:light}
html[data-theme="dark"]{color-scheme:dark}

.pf-theme-btn{position:fixed;right:18px;bottom:18px;z-index:9999;
  display:inline-flex;align-items:center;gap:7px;
  padding:9px 14px 9px 11px;border-radius:999px;cursor:pointer;
  font:inherit;font-size:13px;line-height:1;
  background:rgba(128,128,128,.14);backdrop-filter:blur(12px);
  border:1px solid rgba(128,128,128,.34);
  color:inherit;opacity:.72;
  transition:opacity .2s,background .2s,border-color .2s,transform .2s}
.pf-theme-btn:hover{opacity:1;transform:translateY(-1px);
  border-color:rgba(128,128,128,.7)}
.pf-theme-btn:focus-visible{outline:2px solid currentColor;outline-offset:3px}
.pf-theme-btn svg{width:15px;height:15px;flex:none;
  stroke:currentColor;fill:none;stroke-width:1.7;
  stroke-linecap:round;stroke-linejoin:round}
.pf-theme-btn .pf-theme-label{font-size:12.5px}
@media (max-width:640px){.pf-theme-btn .pf-theme-label{display:none}
  .pf-theme-btn{padding:10px;border-radius:50%}}
@media print{.pf-theme-btn{display:none}}
"""

ENGINE_JS = f"""<script>
/* ══ ДВИЖОК ТЕМЫ ══
   Кнопка читает то, что уже выставил скрипт в <head>, и показывает
   обратное состояние: нажатие — это всегда переключение в другую тему.
   Выбор пишется в localStorage, чтобы не прыгал между страницами. */
(function(){{
  var KEY='{STORAGE_KEY}';
  var SUN='<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>';
  var MOON='<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>';

  var btn=document.createElement('button');
  btn.type='button';
  btn.className='pf-theme-btn';
  btn.setAttribute('data-{ENGINE_MARKER}','');
  btn.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"></svg>'
    + '<span class="pf-theme-label"></span>';
  document.body.appendChild(btn);

  var icon=btn.querySelector('svg');
  var label=btn.querySelector('.pf-theme-label');
  var root=document.documentElement;

  function paint(){{
    var dark=root.getAttribute('data-theme')==='dark';
    icon.innerHTML=dark?SUN:MOON;
    label.textContent=dark?'Светлая':'Тёмная';
    btn.setAttribute('aria-label',dark?'Включить светлую тему':'Включить тёмную тему');
    btn.title=btn.getAttribute('aria-label');
  }}

  btn.addEventListener('click',function(){{
    var next=root.getAttribute('data-theme')==='dark'?'light':'dark';
    root.setAttribute('data-theme',next);
    try{{localStorage.setItem(KEY,next)}}catch(e){{}}
    paint();
  }});

  paint();

  /* Системная настройка как тема по умолчанию: если пользователь
     ничего не выбирал, страница следует за системой на лету. */
  var mq=window.matchMedia('(prefers-color-scheme: dark)');
  var onSystem=function(e){{
    var saved=null; try{{saved=localStorage.getItem(KEY)}}catch(err){{}}
    if(saved==='light'||saved==='dark') return;
    root.setAttribute('data-theme',e.matches?'dark':'light');
    paint();
  }};
  if(mq.addEventListener) mq.addEventListener('change',onSystem);
  else if(mq.addListener) mq.addListener(onSystem);
}})();
</script>"""


# ── Сборка страницы ─────────────────────────────────────────────────

def apply(path):
    """Ставит движок темы на одну страницу. Возвращает строку отчёта."""
    src = path.read_text(encoding="utf-8")

    # Снимаем предыдущий накат, чтобы повторный запуск не дублировал код
    src = re.sub(
        r"\n?<!-- " + ENGINE_MARKER + r" -->.*?<!-- /" + ENGINE_MARKER + r" -->\n?",
        "", src, flags=re.S,
    )

    style = re.search(r"<style[^>]*>(.*?)</style>", src, re.S)
    if not style:
        return f"{path.name:28} нет <style> — пропуск"

    var_lines, hard_rules = build_light_css(style.group(1))

    # Порядок блоков важен: переменные идут первыми, потому что
    # правила-переопределения ниже ссылаются на них через var().
    light_vars = ("html[data-theme=\"light\"]{\n" + ";\n".join(var_lines) + "\n}"
                  if var_lines else "")

    theme_css = (
        f"\n<!-- {ENGINE_MARKER} -->\n"
        f"<style>\n{ENGINE_CSS}\n{light_vars}\n" + "\n".join(hard_rules) + "\n</style>"
    )

    src = src[:style.end()] + theme_css + src[style.end():]

    # Скрипт без вспышки — как можно раньше в <head>
    head = re.search(r"<head[^>]*>", src)
    if head:
        src = (src[:head.end()] + "\n" + NO_FLASH_JS
               + f"\n<!-- /{ENGINE_MARKER} -->" + src[head.end():])

    src = src.replace("</body>", f"{ENGINE_JS}\n</body>")

    path.write_text(src, encoding="utf-8")
    return (f"{path.name:28} переменных {len(var_lines):2} · "
            f"правил {len(hard_rules):3}")


def main():
    pages = [p for p in sorted(BASE.glob("*.html"))
             if not p.name.startswith(SKIP_PREFIX)]
    print("Движок тем · тема по умолчанию — системная\n")
    for page in pages:
        print("  " + apply(page))
    print(f"\nГотово: {len(pages)} страниц.")


if __name__ == "__main__":
    main()
