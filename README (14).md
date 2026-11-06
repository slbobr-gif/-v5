# Путник

Пешее путешествие от Кремля до Териберки на твоих шагах. Сергей, 34 года, решил увидеть море, китов и северное сияние — и пошёл пешком. Каждый твой шаг — пять его шагов. По пути: люди, деревни, существа из русских преданий, выбор с последствиями, голод и холод, утренние мысли.

**Статус:** MVP v5 для теста на круге близких (Android, без сервера). Концепция и правила — [docs/PROMPT-v5.md](docs/PROMPT-v5.md).

## Получить APK

[docs/HOWTO-APK.md](docs/HOWTO-APK.md) — загрузить в GitHub, APK соберётся сам; там же — как подключить AppMetrica.

## Устройство

| Папка | Что внутри |
|---|---|
| `app/lib/engine` | Игровой движок — чистый Dart, повторяет эталон `tools/sim/engine.py` |
| `app/lib/{app,data,platform,analytics,ui}` | Состояние, загрузка, каналы к Android, аналитика, экраны |
| `app/android-overlay` | Kotlin: шагомер телефона, Health Connect, уведомления; манифест, иконки |
| `app/assets/content` | Все тексты: главы, места, события, квесты, существа, утренние мысли |
| `app/assets/balance.json` | Все числа игры |
| `app/assets/art` | Иллюстрации (собственные SVG) |
| `app/assets/map` | Карта: линия маршрута и география |
| `tools/` | Валидатор контента, симулятор баланса, сборка карты, генератор графики, проверки |
| `docs/` | Промт v5, журнал решений, архитектура, схема контента, библия, арт-гайд, план теста |
| `.claude/agents/` | Команда из 16 агентов |
| `backend/` | Сервер этапа 0 v1 — заморожен до теста |

## Проверки (без Flutter)

```bash
python3 tools/content/validate.py --strict   # контент по схеме
python3 tools/check_l10n.py                  # строки интерфейса
python3 tools/check_layers.py                # слои архитектуры
python3 tools/sim/simulate.py                # баланс на типичных игроках
python3 tools/sim/make_parity_fixture.py     # эталон для теста совпадения движков
python3 tools/map/build_map.py [--online]    # карта
```

Flutter-тесты (`app/test`) и сборка APK запускаются в GitHub Actions.
