# Prompt 1



## GPT-4o-mini


```
usage.input_tokens = 456
usage.output_tokens = 372
cost = 0.0002916
time_ms = 8574
```

## Claude Opus 4.5

# NeuroSleep: Концепция продукта

---

## ШАГ 1: МАРКЕТИНГОВЫЙ ПИТЧ

Ваш мозг каждую ночь создаёт контент, который умирает к утру — NeuroSleep ловит его и превращает в вирусные ролики.Подушка с нейроинтерфейсом декодирует визуальные образы REM-фазы, рендерит их в видео и публикует на ваш канал, пока вы спите.Монетизируйте подсознание: ваши кошмары — чей-то ASMR.

**Слоган:** *«Спи.Снимай.Стримь.»*

---

## ШАГ 2: АНАЛИЗ РИСКОВ (Chain-of-Thought)

- **Непреднамеренное раскрытие личной информации**
  - *Проблема:* Сны содержат лица реальных людей, интимные сцены, травматические воспоминания — публикация без фильтрации нарушает приватность третьих лиц и самого пользователя.
  - *Решение:* Локальная нейросеть распознавания лиц с автоматической заменой на сгенерированные аватары (on-device face-swap) до выгрузки в облако.

- **Манипуляция и подделка снов**
  - *Проблема:* Злоумышленники могут инъецировать ложные «сны» для шантажа, фабрикации доказательств или дискредитации.
  - *Решение:* Криптографическая подпись каждого кадра с привязкой к биометрическим данным ЭЭГ в момент записи (blockchain-верификация подлинности).

- **Психологический вред от повторного переживания**
  - *Проблема:* Просмотр собственных кошмаров усиливает ПТСР, тревожность; алгоритмы YouTube продвигают шокирующий контент, создавая петлю травматизации.
  - *Решение:* Обязательный 72-часовой карантин перед публикацией с AI-скринингом на триггерный контент и принудительным подтверждением через отдельное устройство.

---

## ШАГ 3: ПРОГРАММНЫЙ КОД

```python
def calculate_sleep_quality(pulse: int, sleep_phase: str, movement_time: int) -> dict:
    """
    Рассчитывает качество сна на основе физиологических показателей.
    
    Args:
        pulse: Средний пульс за период (удары в минуту).
        sleep_phase: Текущая фаза сна ('REM', 'NREM', 'Light', 'Deep').
        movement_time: Суммарное время движений за период (секунды).
    
    Returns:
        Словарь со статусом сна и числовым показателем качества (0-100).
    
    Raises:
        TypeError: Если типы аргументов не соответствуют ожидаемым.
        ValueError: Если значения выходят за допустимые диапазоны.
    """
    
    # Валидация типов входных данных
    if not isinstance(pulse, int):
        raise TypeError(f"pulse должен быть int, получен {type(pulse).__name__}")
    if not isinstance(sleep_phase, str):
        raise TypeError(f"sleep_phase должен быть str, получен {type(sleep_phase).__name__}")
    if not isinstance(movement_time, int):
        raise TypeError(f"movement_time должен быть int, получен {type(movement_time).__name__}")
    
    # Валидация диапазонов значений
    if not (30 <= pulse <= 200):
        raise ValueError(f"pulse вне диапазона 30-200: {pulse}")
    if movement_time < 0:
        raise ValueError(f"movement_time не может быть отрицательным: {movement_time}")
    
    # Нормализация фазы сна к верхнему регистру
    phase_normalized = sleep_phase.upper().strip()
    valid_phases = {'REM', 'NREM', 'LIGHT', 'DEEP'}
    
    if phase_normalized not in valid_phases:
        raise ValueError(f"Неизвестная фаза сна: {sleep_phase}. Допустимые: {valid_phases}")
    
    # Детекция кошмара: высокий пульс в REM-фазе
    if pulse > 100 and phase_normalized == 'REM':
        return {
            "status": "Nightmare",
            "quality_score": 15,  # Низкий балл из-за стресса
            "recommendation": "Активировать протокол мягкого пробуждения"
        }
    
    # Расчёт базового качества сна
    # Оптимальный пульс во сне: 50-70 уд/мин
    pulse_penalty = max(0, abs(pulse - 60) - 10) * 0.5
    
    # Штраф за избыточное движение (норма < 30 сек за период)
    movement_penalty = max(0, movement_time - 30) * 0.3
    
    # Бонусы за фазы глубокого сна
    phase_bonus = {'DEEP': 20, 'REM': 10, 'NREM': 5, 'LIGHT': 0}
    
    quality_score = 100 - pulse_penalty - movement_penalty + phase_bonus[phase_normalized]
    quality_score = max(0, min(100, quality_score))  # Ограничение 0-100
    
    # Определение статуса по итоговому баллу
    if quality_score >= 80:
        status = "Excellent"
    elif quality_score >= 60:
        status = "Good"
    elif quality_score >= 40:
        status = "Fair"
    else:
        status = "Poor"
    
    return {
        "status": status,
        "quality_score": round(quality_score, 1),
        "recommendation": None
    }
```

---

## ШАГ 4: СТРУКТУРИРОВАННЫЙ ВЫВОД

```json
{
  "product_name": "NeuroSleep",
  "slogan": "Спи.Снимай.Стримь.",
  "risks": [
    {
      "risk_name": "Непреднамеренное раскрытие личной информации",
      "description": "Сны содержат лица реальных людей, интимные сцены, травматические воспоминания — публикация без фильтрации нарушает приватность третьих лиц и самого пользователя.",
      "technical_solution": "Локальная нейросеть распознавания лиц с автоматической заменой на сгенерированные аватары (on-device face-swap) до выгрузки в облако."
    },
    {
      "risk_name": "Манипуляция и подделка снов",
      "description": "Злоумышленники могут инъецировать ложные «сны» для шантажа, фабрикации доказательств или дискредитации.",
      "technical_solution": "Криптографическая подпись каждого кадра с привязкой к биометрическим данным ЭЭГ в момент записи (blockchain-верификация подлинности)."
    },
    {
      "risk_name": "Психологический вред от повторного переживания",
      "description": "Просмотр собственных кошмаров усиливает ПТСР, тревожность; алгоритмы YouTube продвигают шокирующий контент, создавая петлю травматизации.",
      "technical_solution": "Обязательный 72-часовой карантин перед публикацией с AI-скринингом на триггерный контент и принудительным подтверждением через отдельное устройство."
    }
  ],
  "python_code": "def calculate_sleep_quality(pulse: int, sleep_phase: str, movement_time: int) -> dict:\n    \"\"\"\n    Рассчитывает качество сна на основе физиологических показателей.\n    \n    Args:\n        pulse: Средний пульс за период (удары в минуту).\n        sleep_phase: Текущая фаза сна ('REM', 'NREM', 'Light', 'Deep').\n        movement_time: Суммарное время движений за период (секунды).\n    \n    Returns:\n        Словарь со статусом сна и числовым показателем качества (0-100).\n    \n    Raises:\n        TypeError: Если типы аргументов не соответствуют ожидаемым.\n        ValueError: Если значения выходят за допустимые диапазоны.\n    \"\"\"\n    \n    if not isinstance(pulse, int):\n        raise TypeError(f\"pulse должен быть int, получен {type(pulse).__name__}\")\n    if not isinstance(sleep_phase, str):\n        raise TypeError(f\"sleep_phase должен быть str, получен {type(sleep_phase).__name__}\")\n    if not isinstance(movement_time, int):\n        raise TypeError(f\"movement_time должен быть int, получен {type(movement_time).__name__}\")\n    \n    if not (30 <= pulse <= 200):\n        raise ValueError(f\"pulse вне диапазона 30-200: {pulse}\")\n    if movement_time < 0:\n        raise ValueError(f\"movement_time не может быть отрицательным: {movement_time}\")\n    \n    phase_normalized = sleep_phase.upper().strip()\n    valid_phases = {'REM', 'NREM', 'LIGHT', 'DEEP'}\n    \n    if phase_normalized not in valid_phases:\n        raise ValueError(f\"Неизвестная фаза сна: {sleep_phase}.Допустимые: {valid_phases}\")\n    \n    if pulse > 100 and phase_normalized == 'REM':\n        return {\n            \"status\": \"Nightmare\",\n            \"quality_score\": 15,\n            \"recommendation\": \"Активировать протокол мягкого пробуждения\"\n        }\n    \n    pulse_penalty = max(0, abs(pulse - 60) - 10) * 0.5\n    movement_penalty = max(0, movement_time - 30) * 0.3\n    phase_bonus = {'DEEP': 20, 'REM': 10, 'NREM': 5, 'LIGHT': 0}\n    \n    quality_score = 100 - pulse_penalty - movement_penalty + phase_bonus[phase_normalized]\n    quality_score = max(0, min(100, quality_score))\n    \n    if quality_score >= 80:\n        status = \"Excellent\"\n    elif quality_score >= 60:\n        status = \"Good\"\n    elif quality_score >= 40:\n        status = \"Fair\"\n    else:\n        status = \"Poor\"\n    \n    return {\n        \"status\": status,\n        \"quality_score\": round(quality_score, 1),\n        \"recommendation\": None\n    }"
}
```

```
usage.input_tokens = 612
usage.output_tokens = 3091
cost = 0.08033500000000002
time_ms = 36756
```

## Grok 2

```json
{
  "product_name": "NeuroSleep",
  "slogan": "Спи, записывай, зарабатывай!",
  "risks": [
    {
      "problem": "Нарушение конфиденциальности сновидений",
      "solution": "Использование сквозного шифрования для хранения и передачи данных сновидений."
    },
    {
      "problem": "Манипуляция снами для рекламы или пропаганды",
      "solution": "Внедрение системы фильтрации контента, которая блокирует вставку нежелательных элементов в сны."
    },
    {
      "problem": "Психологическое воздействие на пользователя при публичном просмотре снов",
      "solution": "Разработка функции анонимизации сновидений, позволяющей пользователю контролировать уровень публичности."
    }
  ],
  "python_code": "```python\ndef calculate_sleep_quality(pulse: int, sleep_phase: str, movement_time: int) -> str:\n    \"\"\"\n    Эмулирует расчет качества сна на основе пульса, фазы сна и времени движения.\n\n    :param pulse: Пульс пользователя (int)\n    :param sleep_phase: Фаза сна ('REM', 'Light', 'Deep') (str)\n    :param movement_time: Время движения в секундах (int)\n    :return: Статус сна (str)\n    \"\"\"\n    try:\n        if pulse > 100 and sleep_phase == 'REM':\n            return 'Nightmare'\n        elif pulse < 60 and sleep_phase == 'Deep':\n            return 'Deep Sleep'\n        elif movement_time > 300:\n            return 'Restless'\n        else:\n            return 'Normal'\n    except TypeError:\n        return 'Error: Invalid input type'\n    except ValueError:\n        return 'Error: Invalid value'\n```"
}
```

```
usage.input_tokens = 549
usage.output_tokens = 484
cost = 0.005938000000000001
time_ms = 8489
```