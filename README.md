# Портфолио — Евгений Андреев

[![Live](https://img.shields.io/badge/live-andreevgeny.github.io%2Fportfolio-2563EB)](https://andreevgeny.github.io/portfolio/)
[![Release](https://img.shields.io/github/v/release/andreevgeny/portfolio?color=success)](https://github.com/andreevgeny/portfolio/releases)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-deployed-222222?logo=github)](https://andreevgeny.github.io/portfolio/)
[![HTML5](https://img.shields.io/badge/HTML5-static-E34F26?logo=html5&logoColor=white)](index.html)
[![No build](https://img.shields.io/badge/build-none-lightgrey)](index.html)

Живая страница: **https://andreevgeny.github.io/portfolio/**

## Огород

Этот репозиторий — одна грядка. На ней растут одиннадцать страниц
и одна Python-модель (`sorterlab/`). Грядка статическая: HTML, CSS
и ванильный JavaScript, без сборки и без зависимостей от чужих CDN —
откроется и без сети, и на бумаге.

У грядки есть соседи. Почва, из которой всё растёт, — мастер-файлы
(`RESUME_MASTER.md`, `DESIGN_STANDARD.md`, `COMPETENCE_HUB.md`,
`NEXT_STEPS.md`, `OVERVIEW.html`) — лежит в облачном Obsidian и
сюда не попадает. Тёплая мастерская, где обкатываются две ветки
дохода, — отдельный проект `lidlab/` рядом, тоже под рукой, но не
в публичном репо. Здесь — **только то, что можно показать нанимателю**.
Никаких стоп-листов и «оценок на глаз» внутри, никаких черновиков
и внутренних сомнений наружу.

Дорожки между грядками протоптаны ссылками в `index.html`. Каждая
ведёт на живой код или живую страницу: в разделе «Артефакты» нет ни
одной цифры, которую нельзя проверить в один клик.

## Структура

Страницы лежат в корне — это и есть сайт, их адреса отдаёт GitHub
Pages (`/portfolio/ux.html`). Всё остальное разложено по папкам.

### Страницы (корень)

| Файл | Что внутри |
|---|---|
| `index.html` | Главная: четыре направления работы, артефакты, хронология, пять резюме под роли |
| `value.html` | Ценностное предложение |
| `viral.html` | Разбор виральных механик: хуки, удержание, петли, арка, метрики |
| `writing.html` | Тексты и редактура: коммерческие нарративы, тон, структуры |
| `archetypes.html` | Архетипы в UHNWI-сервисе: типология резидентов и стандарты |
| `models.html` | AI-бенчмарк моделей: фильтры по производителю, специализации и личному опыту |
| `ux.html` | UX-кейс кабинета самозанятого |
| `qa.html` | QA-аудит живого прототипа |
| `sorterlab.html` | Кейс системного анализа сортировочного центра |
| `sorterlab-simulator.html` | Самостоятельная параметрическая модель с ползунками |

### Папки

| Папка | Что внутри |
|---|---|
| `resumes/` | Пять резюме под роли: `.md` — источник, `.html` — то, что открывают и печатают в PDF |
| `assets/css/` | `design.css` — палитра, типографика, шкала отступов, правила печати |
| `assets/js/` | `theme.js` — переключатель темы; `sorterlab-model.js` — логика браузерного симулятора |
| `assets/img/` | Фотографии и обложка для соцсетей |
| `sorterlab/` | Python-пакет модели: валидация, расчёт мощностей, симуляция, CLI |
| `tests/` | Тесты (`pytest -q`) |
| `tools/` | Скрипты сборки и проверки, см. ниже |
| `.github/workflows/` | Автоматический релиз |

### `tools/` — скрипты

| Файл | Что делает |
|---|---|
| `check_links.py` | Проверяет, что каждая ссылка ведёт на живой файл; нет `href="#"`, нет битых путей |
| `check_contrast.py` | Проверка контраста по WCAG 2.1, AA |
| `probe_contrast.py` | То же, но в живом DOM через headless-Chrome |
| `apply_design.py` | Раскатка дизайн-системы по публичным страницам, идемпотентен |
| `unify_contacts.py` | Раскатка единого блока контактов, идемпотентен |
| `harmonize_pages.py` | Согласование вёрстки страниц |
| `add_social_meta.py` | og:/twitter:/canonical, идемпотентен |
| `build_resume_html.py` | Сборка HTML-версий резюме из `resumes/*.md` |
| `build_resume_pdf.py` | Печать резюме в PDF, по одной странице A4 на роль |
| `print_preview.py` | Превью печатной версии страницы картинкой |
| `shot.py` | Скриншоты в обеих темах для визуальной проверки |
| `changelog.py` | Сводка сессий из `NEXT_STEPS.md` (живёт в Obsidian) |
| `og_card.html` | Шаблон обложки OG/Twitter |

Скрипты считают корнем проекта папку на уровень выше себя, поэтому
их можно запускать откуда угодно:

```bash
python3 tools/check_links.py
```

Каталоги с подчёркиванием в начале (`_drafts/`, `_archive/`, `_shots/`)
в репозиторий не попадают — это рабочие артефакты, не для показа.

## Локальный просмотр

```bash
python3 -m http.server 8000
# http://localhost:8000
```

## SorterLab (Python)

```bash
python3 -m pip install -e .
python3 -m pytest -q
python3 -m sorterlab.cli capacity
python3 -m sorterlab.cli simulate --minutes 10 --format json
```

Подробности: [`sorterlab/README.md`](sorterlab/README.md).

## Что нужно сделать перед коммитом

```bash
# контраст палитры (должен вернуть 0)
python3 _check_contrast.py

# тесты
.venv/bin/pytest -q

# печать: тёмные секции — в светлые, скрытое содержимое — видно
python3 _print_preview.py index.html
```

## Релизы

Каждый push в `main` автоматически создаёт релиз с поднятием
patch-версии — workflow `.github/workflows/auto-release.yml`. Чтобы
поднять minor или major, добавьте в сообщение коммита метку
`[minor]` или `[major]`; пропустить релиз — `[norelease]`.
