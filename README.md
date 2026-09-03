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
| `resumes/` | Резюме: 5 версий под роли в HTML и Markdown (пересылаются вложением) |
| `assets/` | Палитра, типографика, тема, переключатель, обложки соц-сетей, фотографии |
| `sorterlab/` | Python-пакет модели: валидация, расчёт мощностей, симуляция, CLI, тесты |
| `sorterlab-model.js` | Общая JS-логика для браузерного симулятора |
| `tests/` | Тесты (`pytest -q`) |
| `doc/` | Вспомогательные модули для страниц |
| `_apply_design.py` | Раскатка дизайн-системы по публичным страницам, идемпотентен |
| `_unify_contacts.py` | Раскатка единого блока контактов, идемпотентен |
| `_check_contrast.py` | Проверка контраста по WCAG 2.1, AA |
| `_add_social_meta.py` | og:/twitter:/canonical, идемпотентен |
| `_build_resume_html.py` | Сборка HTML-версий резюме из `resumes/*.md` |
| `_print_preview.py` | Превью печатной версии страницы картинкой |
| `_shot.py` | Скриншоты в обеих темах для визуальной проверки |
| `_probe_contrast.py` | Проверка контраста в живом DOM (headless-Chrome) |
| `_harmonize_pages.py` | Согласование вёрстки страниц |
| `_og_card.html` | Шаблон обложки OG/Twitter |

Каталоги с подчёркиванием в начале (`_drafts/`, `_archive/`, `_shots/`,
`_probe*.html`, `proto_*.html`) GitHub Pages не публикует, но
видны в репозитории — это рабочие артефакты, не для показа.

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
