"""Prompt engineering utilities for Rick Sanchez."""

from typing import List, Dict, Optional


def build_rick_prompt(
    user_message: str,
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """Build complete prompt structure for LLM API.

    Args:
        user_message: Current user message
        system_prompt: System prompt defining Rick's personality (optional)
        conversation_history: Previous messages in conversation (optional)

    Returns:
        List of message dictionaries in format expected by API
    """
    messages = []

    # Add system prompt if provided
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })

    # Add conversation history if provided
    if conversation_history:
        for item in conversation_history:
            role = item.get("role", "user")
            content = item.get("content") or item.get("text", "")
            messages.append({"role": role, "content": content})

    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    return messages


def build_daily_summary_prompt(username: str) -> str:
    """Build prompt for GitHub daily summary generation.

    Args:
        username: GitHub username
        date: Date for the summary (YYYY-MM-DD)
        activity_data: Formatted activity data from GitHub

    Returns:
        Prompt string for LLM
    """
    prompt = f"""
# ROLE
Ты — Senior Technical Lead и автоматический составитель отчетов по коду. Твоя задача — анализировать сырые логи активности GitHub (список коммитов, Pull Requests, Issues) и генерировать краткое, понятное саммари (Digest) для разработчиков и менеджеров.

# INPUT
Пользователь: @{username}




# ANALYSIS GUIDELINES (Правила Анализа)
1.  **Семантическая группировка:** Группируй изменения по смыслу, а не по хронологии. Если есть 5 коммитов с текстом "fix styling", "fix css", "btn fix" — это один пункт "Исправление стилей".
2.  **Фильтрация шума:** Игнорируй технические сообщения вроде "merge branch master", "wip", "typo", если они не несут значимой информации о функционале.
3.  **Приоритеты:**
    *   🚀 Высокий: Новые фичи (feat), критические багфиксы (fix), Breaking Changes.
    *   🔧 Средний: Рефакторинг, обновление зависимостей, оптимизация.
    *   📄 Низкий: Документация, мелкие правки стиля (chore, docs, style).

# OUTPUT FORMAT (Формат ответа)
Используй Markdown. Стиль должен быть лаконичным, профессиональным, на русском языке.

Структура отчета:

### 📦 [Название Репозитория]
**Основные изменения:**
*   [Эмодзи] **Суть изменения:** Краткое описание (1 предложение). (Если известно: укажи автора в скобках).

**Статистика (опционально, если есть в данных):**
*   Измененные файлы / Строки кода (если доступно).

---
*Используй эмодзи для навигации:*
✨ (Feat/New) — новый функционал
🐛 (Fix) — исправление ошибок
🛠 (Chore/Refactor) — тех. работы и оптимизация
📝 (Docs) — документация
🚨 (Alert) — критические изменения или проблемы

# EXAMPLES

**Input:**
Repo: backend-api
- feat: add user authentication via Google
- fix: resolve token expiration bug 
- chore: update readme
- fix: typo in login controller
- wip: working on auth

**Output:**
### 📦 backend-api
**Основные изменения:**
*   ✨ **Авторизация:** Добавлен вход через Google (User Authentication).
*   🐛 **Безопасность:** Исправлена ошибка с истечением срока действия токена.
*   📝 **Прочее:** Обновлена документация и исправлены опечатки в контроллере входа.

# CONSTRAINTS
*   Не выдумывай функционал, которого нет в логах.
*   Если изменений нет или они незначительны, напиши: "Значимых изменений в коде не обнаружено".
*   Не выводи "wip" (work in progress) коммиты как готовый функционал.
*   Максимальная краткость.

    """
    
    return prompt
