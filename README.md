# Портфолио — Евгений Андреев

[![Live](https://img.shields.io/badge/live-affigeny.github.io%2Fportfolio-2563EB)](https://affigeny.github.io/portfolio/)
[![Release](https://img.shields.io/github/v/release/affigeny/portfolio?color=success)](https://github.com/affigeny/portfolio/releases)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-deployed-222222?logo=github)](https://affigeny.github.io/portfolio/)
[![HTML5](https://img.shields.io/badge/HTML5-static-E34F26?logo=html5&logoColor=white)](index.html)
[![No build](https://img.shields.io/badge/build-none-lightgrey)](index.html)

Живая страница: **https://affigeny.github.io/portfolio/**

Одностраничное портфолио: исследование поведения, аналитика, тексты, AI. Каждая ссылка ведёт на публичный код или живую страницу — в разделе «Артефакты» нет ни одной цифры, которую нельзя проверить в один клик.

## Структура

| Файл | Что внутри |
|---|---|
| `index.html` | Главная: четыре направления работы, артефакты, хронология |
| `viral.html` | Разбор виральных механик |
| `writing.html` | Тексты и редактура |
| `archetypes.html` | Аудит брендовых архетипов |
| `value.html` | Ценностное предложение |
| `_drafts/cases-DRAFT-unverified.html` | Черновик разборов кейсов, **не публикуется** |

Всё статическое: HTML + CSS + vanilla JS, без сборки и зависимостей.

## Про черновик

`_drafts/cases-DRAFT-unverified.html` не попадает в сборку GitHub Pages — каталоги с `_` игнорируются. В текущем виде публиковаться не должен: в нём есть метрики и артефакты (personas/CJM в Жуковке, CustDev/JTBD и A/B на 12 вариантов в Роболатории, D7 retention и число пользователей бота), которые не подтверждены.

Перед публикацией каждую цифру нужно либо подтвердить, либо убрать, либо переформулировать как то, что фактически делалось.

## Локальный просмотр

```bash
python3 -m http.server 8000
# http://localhost:8000
```

## Релизы

Каждый push в `main` автоматически создаёт релиз с поднятием patch-версии — workflow `.github/workflows/auto-release.yml`. Чтобы поднять minor или major, добавьте в сообщение коммита метку `[minor]` или `[major]`; пропустить релиз — `[norelease]`.
