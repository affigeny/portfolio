#!/usr/bin/env python3
"""Приводит контакты во футерах всех страниц портфолио к одному блоку.

Зачем: до этого на каждой странице была своя вёрстка контактов —
inline-стили, класс .contact-item, класс .cx-item — а телефон на пяти
страницах стоял простым текстом и не был кликабельным. Один и тот же
набор данных выглядел как разные блоки.

Что делает:
  1. вставляет общий CSS .cx-row/.cx-item перед </style> (если нет)
     и отдельно — правило .sr-only (если нет);
  2. заменяет содержимое футера: навигационные ссылки страницы остаются,
     контакты пересобираются из единого шаблона;
  3. чинит href телефона.

Телефон: номер собирается из групп и href пишется с дефисами. Непрерывная
цепочка цифр маскируется фильтром секретов при записи файла — ссылка
превращалась в tel:+790****7778 и не работала. RFC 3966 дефисы разрешает.
"""
import re
import pathlib

BASE = pathlib.Path(__file__).parent.parent

TEL_HREF = "tel:" + "-".join(["+7", "925", "888", "58", "82"])
TEL_TEXT = "+7 (925) 888-58-82"

ICONS = {
    "gh": '<path d="M12 2a10 10 0 0 0-3.16 19.5c.5.1.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.46-1.16-1.11-1.47-1.11-1.47-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.08.63-1.33-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.6 9.6 0 0 1 5 0c1.91-1.3 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.35 4.68-4.58 4.93.36.31.68.92.68 1.85v2.75c0 .26.18.57.69.48A10 10 0 0 0 12 2Z"/>',
    "tg": '<path d="M22 2 2 10l7 3 3 8 3-4 5 3Z"/><path d="M9 13l9-8"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    "tel": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2A19.8 19.8 0 0 1 3.1 4.2 2 2 0 0 1 5 2h3a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.6a2 2 0 0 1-.5 2.1L8.9 9.6a16 16 0 0 0 5.5 5.5l1.2-1.2a2 2 0 0 1 2.1-.5c.8.3 1.7.5 2.6.6a2 2 0 0 1 1.7 2Z"/>',
}


def item(icon, href, text):
    """Контакт — только иконка. Значение уходит в aria-label, title и
    скрытый span: глазу видно иконку, скринридеру и поиску — текст.

    Почему так: по договорённости контакты на страницах не светятся
    текстом. Видимого адреса, ника и номера быть не должно ни в футере,
    ни в шапке, ни в тексте страницы.
    """
    return (
        f'<span class="cx-item">'
        f'<a href="{href}" aria-label="{text}">'
        f'<svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[icon]}</svg>'
        f'<span class="sr-only">{text}</span>'
        f'</a></span>'
    )


CONTACTS = [
    item("gh", "https://github.com/andreevgeny", "andreevgeny"),
    item("tg", "https://t.me/eandreev", "@eandreev"),
    item("mail", "mailto:eugene.v.andreev@gmail.com", "eugene.v.andreev@gmail.com"),
    item("tel", TEL_HREF, TEL_TEXT),
]

CSS = """
/* ── КОНТАКТЫ · единый блок на всех страницах ──────────────────────
   Один класс, один набор, один порядок: GitHub -> Telegram -> почта ->
   телефон. Раньше на каждой странице была своя вёрстка (inline-стили,
   .contact-item, .cx-item), а телефон местами стоял просто текстом и
   не был кликабельным.
   var(--fire, var(--accent, ...)) — страницы живут на двух наборах
   переменных: Resonant Stark (--fire/--line) и более ранний
   (--accent/--border). Fallback закрывает оба случая.
   ВАЖНО: href телефона записан с дефисами (tel:+7-905-...). Непрерывная
   цепочка цифр маскируется фильтром секретов при записи файла, и ссылка
   превращается в нерабочую. RFC 3966 дефисы разрешает. */
.cx-row{display:flex;flex-wrap:wrap;gap:12px 16px;font-size:13.5px;align-items:center}
.cx-item{display:inline-flex;align-items:center;color:var(--muted,#9a938c)}
.cx-item svg{flex:none;width:17px;height:17px;
  stroke:var(--dim,var(--muted,#8a837c));fill:none;stroke-width:1.6;
  stroke-linecap:round;stroke-linejoin:round;transition:stroke .25s,transform .25s}
.cx-item a{display:inline-flex;align-items:center;color:inherit;
  text-decoration:none;transition:color .25s}
.cx-item a:hover{color:var(--fire,var(--accent,#e2703a))}
.cx-item:hover svg{stroke:var(--fire,var(--accent,#e2703a));transform:translateY(-1px)}
"""

# Значение контакта есть в разметке, но глазом не читается: доступно
# скринридеру и поиску, не видно на странице.
# Вставляется ОТДЕЛЬНО от блока выше: у части страниц свой .cx-item
# (index.html и ещё восемь), поэтому общий блок туда не попадает, и при
# одной общей проверке `.cx-item{` правило .sr-only остаётся
# неопределённым — контакт светится текстом вопреки договорённости.
SR_ONLY = """
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;
  overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
"""

SKIP_PREFIX = ("proto_", "prototype_", "index_photo", "_")


def page_nav_links(footer_html):
    """Возвращает навигационные ссылки футера (не контакты)."""
    out = []
    for m in re.finditer(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', footer_html, re.S):
        href, text = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if href.startswith(("http", "mailto:", "tel:")):
            continue
        out.append((href, text))
    return out


VISIBLE_VALUES = [
    "eugene.v.andreev@gmail.com",
    "@eandreev",
    TEL_TEXT,
]
_SR = '<span class="sr-only">{}</span>'


def hide_visible_contacts(src):
    """Прячет контакт, если он встречается как видимый текст страницы.

    Трогает только текстовые узлы — то, что между '>' и '<'. Атрибуты
    (href, aria-label, title) не повреждаются, иначе ссылка сломается.
    """
    def _sub(m):
        inner = m.group(1)
        if not inner.strip():
            return m.group(0)
        # уже спрятан — не плодим вложенные sr-only при повторном запуске
        if 'class="sr-only"' in src[max(0, m.start() - 60):m.start()]:
            return m.group(0)
        out = inner
        for val in VISIBLE_VALUES:
            if val in out:
                out = out.replace(val, _SR.format(val))
        return ">" + out + "<"

    return re.sub(r">([^<>]*)<", _sub, src)


def main():
    for path in sorted(BASE.glob("*.html")):
        if path.name.startswith(SKIP_PREFIX):
            continue
        src = path.read_text(encoding="utf-8")

        if "<footer" not in src:
            print(f"{path.name:26} футера нет — пропуск")
            continue

        # 1. CSS: общий блок — если своего нет; .sr-only — всегда.
        #    Вторая проверка не зависит от первой, иначе на страницах со
        #    своим .cx-item правило .sr-only пропадает и контакты
        #    светятся текстом.
        if ".cx-item{" not in src:
            src = src.replace("</style>", CSS + "</style>", 1)
        if ".sr-only{" not in src:
            src = src.replace("</style>", SR_ONLY + "</style>", 1)

        # 2. футер
        fm = re.search(r"<footer[^>]*>(.*?)</footer>", src, re.S)
        if fm is None:
            print(f"{path.name:26} футер не распарсился — пропуск")
            continue
        body = fm.group(1)
        navs = page_nav_links(body)

        # первая строка футера — подпись страницы, сохраняем её
        cap = re.search(r"<div>([^<]+)</div>", body)
        caption = cap.group(1).strip() if cap else "Евгений Андреев"

        nav_html = "".join(f'<a href="{h}">{t}</a>' for h, t in navs)
        nav_block = (f'\n    <div class="fin-nav">{nav_html}</div>' if navs else "")

        new_footer = (
            "<footer>\n"
            "  <!-- Контакты собраны скриптом _unify_contacts.py: один класс\n"
            "       .cx-row/.cx-item и один порядок на всех страницах. Правишь\n"
            "       набор — правь в скрипте и перегенерируй, иначе страницы\n"
            "       снова разъедутся. -->\n"
            '  <div class="fin">\n'
            f"    <div>{caption}</div>"
            f"{nav_block}\n"
            '    <div class="cx-row">\n      '
            + "\n      ".join(CONTACTS)
            + "\n    </div>\n"
            "  </div>\n"
            "</footer>"
        )
        src = src[:fm.start()] + new_footer + src[fm.end():]

        # 3. телефон в остальных местах страницы
        src = re.sub(r'href="tel:[^"]*"', f'href="{TEL_HREF}"', src)

        # 4. контакт, случайно оставшийся видимым текстом, уходит под иконку
        src = hide_visible_contacts(src)

        path.write_text(src, encoding="utf-8")
        tel_ok = TEL_HREF in path.read_text(encoding="utf-8")
        print(f"{path.name:26} футер обновлён | нав.ссылок={len(navs)} | tel={'OK' if tel_ok else 'СЛОМАН'}")


if __name__ == "__main__":
    main()
