#!/usr/bin/env python3
"""Замеряет реальный контраст текста в браузере, а не по исходникам.

Зачем
-----
`_check_contrast.py` считает пары «токен / фон» из CSS. Он не видит
двух вещей, из-за которых текст становится нечитаемым на живой
странице:

  1. Страница объявляет свой токен (например `--ink`) и перебивает
     дизайн-систему: в CSS пара проходит проверку, в браузере — нет.
  2. Цвет приходит из авторского правила страницы, а не из токена:
     проверка по токенам его не покрывает вовсе.

Этот скрипт берёт вычисленные значения из отрисованной страницы:
обходит элементы с текстом, достаёт `color`, поднимается вверх по
дереву за фактическим фоном (с учётом прозрачности и градиентов) и
считает WCAG-контраст.

Как работает
------------
Страница копируется в корень проекта под именем `.__probe_*.html`
(иначе относительные пути к `assets/` не разрешатся), в конец копии
вставляется замеряющий скрипт, Chrome отдаёт DOM после выполнения JS,
результат читается из `<pre id="PROBE">`. Копия удаляется в finally.

Запуск
------
    python3 _probe_contrast.py                # все публичные страницы
    python3 _probe_contrast.py value.html     # одна страница
    python3 _probe_contrast.py --theme dark   # другая тема
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROBE_RE = re.compile(
    r'<pre id="PROBE"[^>]*>(.*?)</pre>', re.S
)

# Публичные страницы. OVERVIEW.html — со своим движком тем, в общий
# прогон не идёт; проверяется отдельно, если понадобится.
PAGES = [
    "index.html",
    "value.html",
    "ux.html",
    "qa.html",
    "viral.html",
    "writing.html",
    "archetypes.html",
    "models.html",
    "sorterlab.html",
    "sorterlab-simulator.html",
    "OVERVIEW.html",
]

JS = r"""
(function () {
  var THEME = "__THEME__";
  var root = document.documentElement;
  try {
    localStorage.setItem("pf-theme", THEME);
  } catch (e) {}
  root.setAttribute("data-theme", THEME);

  function srgb(c) {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  }
  function lum(rgb) {
    return (
      0.2126 * srgb(rgb[0]) + 0.7152 * srgb(rgb[1]) + 0.0722 * srgb(rgb[2])
    );
  }
  function ratio(a, b) {
    var la = lum(a), lb = lum(b);
    var hi = Math.max(la, lb), lo = Math.min(la, lb);
    return (hi + 0.05) / (lo + 0.05);
  }
  // Любой CSS-цвет -> rgba. Через canvas, а не регуляркой: страницы
  // задают акцент в oklch(), и разбор вида /rgba?\(.../ просто не
  // находил его, из-за чего фон кнопки подменялся фоном страницы и
  // отчёт показывал несуществующие провалы.
  var cv = document.createElement("canvas");
  cv.width = cv.height = 1;
  var ctx = cv.getContext("2d", { willReadFrequently: true });
  function parse(str) {
    if (!str) return null;
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = "#000";
    ctx.fillStyle = str; // непонятный формат оставляет чёрный, не undefined
    ctx.fillRect(0, 0, 1, 1);
    var d = ctx.getImageData(0, 0, 1, 1).data;
    return { r: d[0], g: d[1], b: d[2], a: d[3] / 255 };
  }
  function over(fg, bg) {
    return [
      fg.r * fg.a + bg.r * (1 - fg.a),
      fg.g * fg.a + bg.g * (1 - fg.a),
      fg.b * fg.a + bg.b * (1 - fg.a),
    ];
  }
  // Фактический фон: поднимаемся вверх, пока не найдём непрозрачный
  // слой. Градиенты и картинки помечаем — по ним цвет не вычислить,
  // и молча принять их за «нет фона» значит получить ложную тревогу
  // или, что хуже, пропустить реальную.
  // Худший случай по стопам градиента: если где-то в градиентной
  // заливке есть светлый стоп, именно на нём текст и пропадёт.
  function gradientStops(str) {
    if (!str || str === "none") return [];
    var re = /(#[0-9a-f]{3,8}|rgba?\([^)]*\)|oklch\([^)]*\)|oklab\([^)]*\)|hsla?\([^)]*\)|color\([^)]*\))/gi;
    var out = [];
    var m;
    while ((m = re.exec(str))) {
      var c = parse(m[1]);
      if (c) out.push(c);
    }
    return out;
  }

  function effectiveBg(el) {
    var stack = [];
    var node = el;
    var unresolved = false;
    while (node && node.nodeType === 1) {
      var cs = getComputedStyle(node);
      var stops = gradientStops(cs.backgroundImage);
      if (stops.length) {
        // Градиент композитится поверх того, что под ним; для оценки
        // берём самый непрозрачный стоп как основной слой.
        var solid = stops.filter(function (c) { return c.a >= 0.999; });
        if (solid.length) stack.push(solid[0]);
        else if (stops.length) stack.push(stops[0]);
        unresolved = stops.length > 1;
      }
      var c = parse(cs.backgroundColor);
      if (c && c.a > 0) {
        stack.push(c);
        if (c.a >= 0.999 && !stops.length) break;
        if (c.a >= 0.999 && stops.length) break;
      }
      node = node.parentElement;
    }
    var base = { r: 255, g: 255, b: 255, a: 1 };
    if (THEME === "dark") base = { r: 0, g: 0, b: 0, a: 1 };
    for (var i = stack.length - 1; i >= 0; i--) {
      base = {
        r: stack[i].r * stack[i].a + base.r * (1 - stack[i].a),
        g: stack[i].g * stack[i].a + base.g * (1 - stack[i].a),
        b: stack[i].b * stack[i].a + base.b * (1 - stack[i].a),
        a: 1,
      };
    }
    return { rgb: [base.r, base.g, base.b], unresolved: unresolved };
  }

  function visible(el) {
    var cs = getComputedStyle(el);
    if (cs.visibility === "hidden" || cs.display === "none") return false;
    if (parseFloat(cs.opacity) === 0) return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function path(el) {
    var parts = [];
    var n = el;
    for (var i = 0; n && n.nodeType === 1 && i < 4; i++) {
      var cls = n.className && typeof n.className === "string"
        ? "." + n.className.trim().split(/\s+/).slice(0, 2).join(".")
        : "";
      parts.unshift(n.tagName.toLowerCase() + cls);
      n = n.parentElement;
    }
    return parts.join(" > ");
  }

  function run() {
    var out = {
      theme: THEME,
      title: document.title,
      bad: [],
      checked: 0,
      decor: 0,
      mock: 0,
    };
    var all = document.querySelectorAll("body *");
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      // Только узлы с собственным текстом: иначе один и тот же цвет
      // всплывёт по всем обёрткам и утопит отчёт.
      var own = "";
      for (var k = 0; k < el.childNodes.length; k++) {
        var nd = el.childNodes[k];
        if (nd.nodeType === 3) own += nd.nodeValue;
      }
      if (!own.trim()) continue;
      if (!visible(el)) continue;

      var cs = getComputedStyle(el);
      var fill = cs.webkitTextFillColor || cs.color;
      var fg = parse(fill);
      if (!fg) continue;
      // Прозрачная заливка — это обводка или текст-градиент, а не
      // цвет символов. Контраст по ней не считается: считаем отдельно.
      if (fg.a === 0) {
        out.decor++;
        continue;
      }
      // Макеты экранов внутри кейса — это картинка прототипа, а не
      // вёрстка сайта: их цвета заданы намеренно и тему не наследуют.
      if (el.closest(".phone, .screen-wrap, .ui-card, .device")) {
        out.mock++;
        continue;
      }
      var bg = effectiveBg(el);
      var fgc = over(fg, { r: bg.rgb[0], g: bg.rgb[1], b: bg.rgb[2] });
      var cr = ratio(fgc, bg.rgb);
      out.checked++;

      var px = parseFloat(cs.fontSize);
      var bold = parseInt(cs.fontWeight, 10) >= 700;
      var large = px >= 24 || (px >= 18.66 && bold);
      var need = large ? 3.0 : 4.5;

      if (cr < need) {
        out.bad.push({
          sel: path(el),
          text: own.trim().slice(0, 46),
          color: cs.color,
          bg: "rgb(" + bg.rgb.map(Math.round).join(",") + ")",
          ratio: Math.round(cr * 100) / 100,
          need: need,
          px: Math.round(px * 10) / 10,
          unresolved: bg.unresolved,
        });
      }
    }
    var pre = document.createElement("pre");
    pre.id = "PROBE";
    pre.textContent = JSON.stringify(out);
    document.body.appendChild(pre);
  }

  setTimeout(run, 400);
})();
"""


def probe(page: str, theme: str) -> dict:
    src_page = ROOT / page
    tmp = ROOT / (".__probe_" + page)
    src = src_page.read_text(encoding="utf-8")
    js = JS.replace("__THEME__", theme)
    src = src.replace("</body>", "<script>" + js + "</script>\n</body>")
    try:
        tmp.write_text(src, encoding="utf-8")
        dom = subprocess.run(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--virtual-time-budget=4000",
                "--window-size=1440,1000",
                "--dump-dom",
                tmp.as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        ).stdout
        m = PROBE_RE.search(dom)
        if not m:
            return {"error": "probe не отработал", "bad": [], "checked": 0}
        import html as _html

        return json.loads(_html.unescape(m.group(1)))
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> int:
    raw = sys.argv[1:]
    theme = "light"
    if "--theme" in raw:
        i = raw.index("--theme")
        if i + 1 < len(raw):
            theme = raw[i + 1]
        del raw[i : i + 2]
    # Значение после --theme не считается именем страницы.
    args = [a for a in raw if not a.startswith("-")]
    pages = args or PAGES

    total = 0
    print(f"Тема: {theme}\n")
    for page in pages:
        if not (ROOT / page).exists():
            print(f"  ! {page} — файла нет")
            continue
        res = probe(page, theme)
        total += len(res.get("bad", []))
        flag = "OK  " if not res.get("bad") else "ПЛОХО"
        err = " · " + res["error"] if res.get("error") else ""
        print(
            f"  [{flag}] {page:28} проверено {res.get('checked', 0):4} · "
            f"ниже порога {len(res.get('bad', []))}{err}"
        )
        for b in res.get("bad", [])[:14]:
            mark = " ~" if b.get("unresolved") else "  "
            print(
                f"        {mark}{b['ratio']:5.2f} (нужно {b['need']}) "
                f"{b['px']:4.1f}px  {b['color']:22} на {b['bg']:18} "
                f"| {b['sel'][:52]} | «{b['text']}»"
            )
    print(f"\nВсего ниже порога: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
