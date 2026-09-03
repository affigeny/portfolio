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

  var THEME_KEY = "pf-theme";
  var METAL_KEY = "pf-metal";

  var THEMES = ["system", "light", "dark"];
  var METALS = ["brass", "bronze", "copper"];

  var THEME_SHORT = { system: "Авто", light: "Светлая", dark: "Тёмная" };
  var THEME_LABEL = {
    system: "Тема: как в системе",
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

  var theme = read(THEME_KEY, THEMES, "system");
  var metal = read(METAL_KEY, METALS, "brass");

  /* Атрибуты ставим сразу, до загрузки DOM: это и есть защита от
     мигания. Кнопки настраиваем позже, когда они появятся в разметке. */
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-metal", metal);

  /* Один обработчик на две оси: различаются только список значений,
     имя атрибута и подписи. Дублировать эту логику ради двух кнопок
     значило бы править одно и то же в двух местах. */
  function bind(selector, attr, order, shorts, labels, key, current) {
    var button = document.querySelector(selector);
    if (!button || button.dataset.bound === "1") return;

    var label = button.querySelector("[data-" + attr + "-label]");
    var value = current;

    function sync() {
      if (label) label.textContent = shorts[value];
      var text = labels[value] + " — нажмите, чтобы сменить";
      button.setAttribute("aria-label", text);
      button.setAttribute("title", text);
    }

    button.dataset.bound = "1";
    button.addEventListener("click", function () {
      value = order[(order.indexOf(value) + 1) % order.length];
      document.documentElement.setAttribute("data-" + attr, value);
      save(key, value);
      sync();
    });

    sync();
  }

  function bindAll() {
    bind("[data-theme-toggle]", "theme", THEMES,
         THEME_SHORT, THEME_LABEL, THEME_KEY, theme);
    bind("[data-metal-toggle]", "metal", METALS,
         METAL_SHORT, METAL_LABEL, METAL_KEY, metal);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindAll);
  } else {
    bindAll();
  }

  /* Кнопка «далее» в плавающем кластере. href уже стоит в разметке
     как обычная ссылка — среднестатистический клик отработает без JS.
     Здесь ловим только модифицированные клики, чтобы будущая
     аналитика (Cmd+клик «открыть в новой вкладке») не ломалась. */
  function bindNext() {
    var btns = document.querySelectorAll("[data-fab-next]");
    for (var i = 0; i < btns.length; i++) {
      var el = btns[i];
      if (el.dataset.boundNext === "1") continue;
      el.dataset.boundNext = "1";
      el.addEventListener("click", function (event) {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button === 1) {
          return;
        }
        event.preventDefault();
        var href = this.getAttribute("data-fab-next") || this.getAttribute("href");
        if (href) window.location.href = href;
      });
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindNext);
  } else {
    bindNext();
  }
})();
