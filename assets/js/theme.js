/* ═══════════════════════════════════════════════════════════════════════
   THEME · переключатель темы и акцентного металла

   Скрипт подключается в <head> без defer и без async. Это сделано
   намеренно: оба атрибута должны быть выставлены до первой отрисовки,
   иначе страница успевает показаться тёмной и только потом
   перекрашивается — на медленном соединении это заметное мигание.

   Две независимые оси, а не одна
   ------------------------------
   Тема отвечает за светлоту: system / light / dark.
   Металл отвечает за акцент: brass / bronze / copper.

   system — следует системной настройке, это значение по умолчанию;
   light и dark — явный выбор. Отдельное состояние system нужно,
   потому что двухпозиционный переключатель при первом же клике
   навсегда отвязывает страницу от системной темы: вернуть «как в
   системе» пользователь уже не может.

   Металл состояния «system» не имеет — система такого не отдаёт.

   Зачем металл, если он ничего не продаёт
   ---------------------------------------
   Переключатель меняет одну переменную — `--accent` — и вся страница
   перекрашивается: кнопки, ссылки, свечение, рамки, маркеры списков.
   Это не украшение, а предъявление: так видно, что вёрстка собрана на
   токенах, а не на цветах, прописанных в каждом правиле. Для
   портфолио, которое показывают продуктовым и фронтенд-командам, это
   аргумент сильнее любой строчки в разделе «навыки».

   Выбор хранится в localStorage под ключами pf-theme и pf-metal. Если
   хранилище недоступно (приватный режим, запрет на данные), скрипт не
   падает, а работает на значениях по умолчанию.
   ═══════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* Два состояния, а не три: «как в системе» убрано. Раньше цикл был
     system → light → dark → system, и при системной светлой теме
     клик «system → light» визуально ничего не менял: обе выглядят
     как светлая. Это и был тот «пустой» клик. Теперь тумблер
     двусторонний: слева свет, справа тьма, ползунок между ними.
     По умолчанию — системная настройка, но на первом же клике
     она фиксируется в явный выбор, и вернуться к «как в системе»
     можно только стерев ключ вручную. Для портфолио это правильно:
     пользователь, который потрогал тумблер, уже выбрал. */
  var THEME_KEY = "pf-theme";
  var METAL_KEY = "pf-metal";
  var THEMES = ["light", "dark"];
  var METALS = ["brass", "bronze", "copper"];

  var THEME_LABEL = {
    light: "Тема: светлая",
    dark: "Тема: тёмная",
  };

  var METAL_SHORT = { brass: "Латунь", bronze: "Бронза", copper: "Медь" };
  var METAL_LABEL = {
    brass: "Акцент: латунь",
    bronze: "Акцент: бронза",
    copper: "Акцент: медь",
  };

  /* Хранилище обёрнуто в try: в приватном режиме Safari обращение к
     localStorage выбрасывает исключение, и без обёртки скрипт умер бы
     на первой же строке, оставив страницу без темы вовсе. */
  function read(key, allowed, fallback) {
    try {
      var value = localStorage.getItem(key);
      return allowed.indexOf(value) === -1 ? fallback : value;
    } catch (error) {
      return fallback;
    }
  }

  function save(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      /* Нечего делать: работаем на значениях по умолчанию. */
    }
  }

  /* Состояние читается один раз, до биндинга. Если бы theme и metal
     объявлялись внутри bindAll, первая смена темы работала, а вторая
     откатывалась — замыкание пересоздавалось. Сейчас это одна
     переменная на всё время жизни скрипта, и счётчик не сбрасывается. */
  var theme = read(THEME_KEY, THEMES, "light");
  var metal = read(METAL_KEY, METALS, "brass");

  /* Атрибуты ставим сразу, до парсинга тела: это и есть защита от
     мигания. Скрипт подключён в <head>, documentElement уже есть,
     а data-theme="dark" на нём заставляет тёмные токены примениться
     ещё до первой отрисовки. */
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-metal", metal);

  /* Делегирование на document, а не на конкретный контейнер.
     Раньше обработчик навешивался на [data-theme-toggle] в момент
     DOMContentLoaded — и это ровно та ловушка, на которую я наступал
     дважды: если скрипт в <head> успевал до парсинга тела, контейнер
     ещё не существовал, querySelector возвращал null, и клик уходил
     в никуда. Делегирование вешает один обработчик на document,
     который проверяет event.target.closest(...) — это работает
     в любом порядке загрузки и для кнопок, добавленных позже. */
  function bindAll() {
    if (document.documentElement.dataset.bound === "1") return;
    document.documentElement.dataset.bound = "1";

    document.addEventListener("click", function (event) {
      var node = event.target.closest(
        "[data-theme-set], [data-metal-toggle], [data-scroll-top]"
      );
      if (!node) return;

      /* Тема: клик по левой ставит свет, по правой — тьму. */
      if (node.hasAttribute("data-theme-set")) {
        var val = node.getAttribute("data-theme-set");
        if (val !== "light" && val !== "dark") return;
        if (val === theme) return;
        theme = val;
        document.documentElement.setAttribute("data-theme", theme);
        save(THEME_KEY, theme);
        syncTheme();
        return;
      }

      /* Металл: трёхпозиционный цикл. */
      if (node.hasAttribute("data-metal-toggle")) {
        metal = METALS[(METALS.indexOf(metal) + 1) % METALS.length];
        document.documentElement.setAttribute("data-metal", metal);
        save(METAL_KEY, metal);
        syncMetal();
        return;
      }

      /* Стрелка «наверх»: плавная прокрутка вместо прыжка. */
      if (node.hasAttribute("data-scroll-top")) {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button === 1) {
          return;
        }
        event.preventDefault();
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }
    });
  }

  /* Синхронизация подписей и подсветки. Делается сразу и при каждом
     клике, но не в цикле биндинга — кнопки могут появиться позже
     скрипта, и тогда первый sync их пропустит. Поэтому вызываем
     sync ещё раз на DOMContentLoaded как страховку. */
  function syncTheme() {
    var opts = document.querySelectorAll("[data-theme-set]");
    for (var i = 0; i < opts.length; i++) {
      var opt = opts[i];
      var val = opt.getAttribute("data-theme-set");
      var on = val === theme;
      opt.classList.toggle("is-active", on);
      opt.setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  function syncMetal() {
    var buttons = document.querySelectorAll("[data-metal-toggle]");
    for (var i = 0; i < buttons.length; i++) {
      var button = buttons[i];
      var label = button.querySelector("[data-metal-label]");
      if (label) label.textContent = METAL_SHORT[metal];
      var text = METAL_LABEL[metal] + " — нажмите, чтобы сменить";
      button.setAttribute("aria-label", text);
      button.setAttribute("title", text);
    }
  }

  function runSync() { syncTheme(); syncMetal(); }

  /* Биндим обработчик как можно раньше — он делегированный, кнопки
     ему не нужны. Но и подстраховываемся: если кнопки появились
     позже вызова, первый клик их подсветит сам. И всё же прогоняем
     sync после парсинга — чтобы aria-pressed и подписи стояли
     правильно ещё до первого клика. */
  bindAll();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runSync);
  } else {
    runSync();
  }
