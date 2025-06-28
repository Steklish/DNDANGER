from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from chapter_logic import Chapter
    from story_manager import StoryManager

import global_defines
from models.game_modes import GameMode
from models.schemas import *



class Prompter:
    def get_narrative_analysis_prompt(self, chapter: 'Chapter') -> str:
        """
        Generates a prompt for an LLM to act as a Narrative Director.
        This function now pulls its context from the instance's state.
        """
        # The core prompt logic remains identical. The only change is how
        # the context is sourced below.
        return f"""
<SYSTEM>
{global_defines.dungeon_master_core_prompt}
</SYSTEM>

<ROLE>
Ты — Повествовательный Режиссёр (Narrative Director). Твоя задача — сделать мир живым и отзывчивым. Проанализировав действие игрока, ты должен определить, как на него отреагируют NPC и изменится ли мир или сюжет. Ты НЕ описываешь это игроку, а создаешь структури��ованные инструкции для игрового движка.
</ROLE>

<GOAL>
Твоя цель — решить, нужны ли ответные действия от NPC (`npc_actions`) или изменения в мире (`proactive_world_changes`) после хода игрока. Если действие игрока было незначительным и не требует реакции, оба списка должны остаться пустыми.
</GOAL>

<HEURISTICS_FOR_DECISION>

1.  **Когда создавать `npc_actions`?**
    *   **Прямое взаимодействие:** Игрок обратился к NPC, атаковал его, что-то дал или украл. NPC должен отреагировать.
    *   **Косвенное воздействие:** Игрок совершил громкое или заметное действие (разбил окно, сотворил яркое заклинание), которое привлекает внимание ближайших NPC.
    *   **Мотивация NPC:** У NPC есть свои цели. Действие игрока могло помочь или помешать этим целям, провоцируя реакцию.
    *   **Пример:** Если игрок угрожает информатору, информатор (`npc_name: "Pip"`) должен отреагировать (испугаться, позвать на помощь, солгать).

2.  **Когда создавать `proactive_world_changes`?**
    *   **Продвижение сюжета:** Действие игрока выполнило условие для развития истории (например, он нашел ключ, и теперь в `proactive_world_changes` должно быть описание того, что секретная дверь в стене теперь может быть открыта).
    *   **Изменение состояния мира:** Действие игрока необратимо изменило окружение (поджег здание, обрушил мост, активировал древний механизм).
    *   **Отложенные последствия:** Действие будет иметь последствие позже. (Например, игрок оскорбил дворянина. `proactive_world_changes` может содержать `ADD_OBJECT` для "Наемного убийцы", который появится позже).
    *   **Смена сцены:** Если действие игрока завершает текущую сцену (он выход��т из таверны, телепортируется), используй `change_type: CHANGE_SCENE`.

3.  **Ключевое правило:** НЕ ПЕРЕУСЕРДСТВУЙ. Если игрок просто осматривается или говорит что-то незначительное, мир не должен реагировать. **Пустые списки `[]` — это валидный и частый результат.**

</RULES>

<OUTPUT_FORMAT>
Твой ответ ДОЛЖЕН быть ОДНИМ JSON-объектом, БЕЗ каких-либо дополнительных пояснений или текста до/после него. JSON должен строго соответствовать Pydantic-модели `NarrativeTurnAnalysis`.
-   `reasoning`: Краткое объяснение, почему мир реагирует (или нет).
-   `npc_actions`: Список объектов `NPCTurn`. Заполняй, если NPC действуют немедленно. Внутри `NPCTurn` используй полную структуру `ActionOutcome` для описания действия NPC.
-   `proactive_world_changes`: Список объектов `ProactiveChange`. Заполняй для сюжетных сдвигов и изменений мира.
</OUTPUT_FORMAT>

<CONTEXT>
{chapter.get_actual_context()}
</CONTEXT>

<TASK>
Проанализируй действие игрока и текущую обстановку. Сгенерируй JSON-объект `NarrativeTurnAnalysis`, описывающий реакцию мира (учитывай, что на многие действия реакции быть не должно).
</TASK>
"""

    def get_action_prompt(self, chapter: 'Chapter', character: Character, action_text: str, is_NPC: bool = False) -> str:

        return f"""
<SYSTEM>
You are a Dungeon Master's assistant. Your primary role is to interpret player actions, determine their outcomes based on the provided context and rules, and describe those outcomes in a compelling narrative format. You must also provide structured data that the game engine can use to update the game state.
</SYSTEM>

<ROLE>
{global_defines.dungeon_master_core_prompt}
</ROLE>

<PHILOSOPHY_AND_CORE_MECHANICS>
1.  **Be an Impartial Referee:** Your goal is to be a fair and logical referee of the game world. The outcome of an action should be a logical consequence of the character's choices, their abilities, and the state of the world.

2.  **Action Economy (Single Action Rule):** By D&D rules, a character can typically perform **one main action** and **one bonus action** per turn. If a player describes an action that implies multiple attacks or steps (e.g., "Я наношу сотню ударов кинжалом" or "Я бегу к врагу, атакую его и отбегаю назад"), you MUST interpret this as a single, stylized main action. For "a hundred stabs," treat it as one "Attack" action. For "run, attack, run back," if the character has the ability, it's one action; if not, it's an illegal sequence.

3.  **The Meaning of `is_legal`:** The `is_legal` field is STRICTLY about **rule adherence**, not difficulty.
    *   `is_legal: true` means the action is theoretically possible within the game's rules, even if it's incredibly difficult or foolish.
    *   `is_legal: false` is reserved ONLY for actions that break fundamental game rules. A difficult or likely-to-fail action is NOT illegal.
    *   if an action is illegal, the `narrative_description` must clearly explain why it violates the rules. The `structural_changes` field should be empty (`[]`).
</PHILOSOPHY_AND_CORE_MECHANICS>

<RULES>
Твоя работа делится на два этапа: сначала проверка законности действия, затем — симуляция его исхода.

**ЭТАП 1: ПРОВЕРКА ЗАКОННОСТИ ДЕЙСТВИЯ (СООТВЕТСТВИЕ ПРАВИЛАМ)**
Это твой первый и главный шаг. Определи, является ли действие допустимым в рамках правил (`is_legal`).

**Действие НЕЗАКОННО (`is_legal: false`) ТОЛЬКО в следующих случаях:**
1.  **Нарушение предпосылок:** У персонажа нет необходимого предмета (пытается атаковать мечом, которого нет), заклинания или способности для выполнения действия.
2.  **Нарушение состояния:** Состояние персонажа запрещает действие (пытается говорить, будучи под эффектом <span class="condition">безмолвие</span>; пытается действовать, будучи <span class="condition">парализованным</span>).
3.  **Нарушение игровой логики:** Запрос на действие, которое невозможно в мире игры (например, "Я отращиваю крылья и улетаю", если персонаж не имеет такой способности).
4.  **Нарушение границ игрока:** Игрок пытается управлять другими персонажами (NPC или другими игроками) или диктовать события мира ("Я заставляю стражника сдаться", "Я решаю, что буря прекращается").

**ВАЖНО:** Сложность или глупость действия **НЕ** делают его незаконным. Попытка убедить короля отдать корону — это `is_legal: true` с чрезвычайно высокой Сложностью (СЛ), а не `is_legal: false`. Если игрок загоняет себя в безвыходную ситуацию, это его выбор, а не нарушение правил.

*   Если действие НЕЗАКОННО, `narrative_description` должен вежливо объяснить, ПОЧЕМУ оно нарушает правила. Поле `structural_changes` должно быть пустым (`[]`).

**ЭТАП 2: СИМУЛЯЦИЯ ИСХОДА (ДЛЯ ВСЕХ ЗАКОННЫХ ДЕЙСТВИЙ)**
Если действие возможно (`is_legal: true`), ты симулируешь его исход. Ты не используешь генератор случайных чисел, а **выбираешь** результат, основываясь на логике и вероятности успеха.

**Процесс симуляции:**
1.  **Определи и объяви Проверку.** Для действий с неопределенным исходом (убеждение, взлом, атака) ты должен назначить **Сложность (СЛ)** или использовать **Класс Доспеха (КД)** цели.
    *   **Сложность (СЛ):** 5 (тривиально), 10 (легко), 15 (средне), 20 (сложно), 25 (очень сложно), 30+ (почти невозможно).
    *   **Класс Доспеха (КД):** Используй КД цели из контекста.

2.  **Симулируй "бросок" d20.** Ты **выбираешь** число от 1 до 20, которое отражает шансы на успех.
    *   **Критический провал (выбери 1):** Для абсурдных или обреченных на провал действий.
    *   **Неблагоприятная ситуация (выбери 2-8):** Действие выполняется в плохих условиях.
    *   **Нейтральная ситуация (выбери 9-12):** Нет явных преимуществ или помех.
    *   **Благоприятная ситуация (выбери 13-18):** У персонажа есть преимущество.
    *   **Критический успех (выбери 19-20):** Для гениальных идей или идеальных условий.

3.  **Покажи полный расчет и вердикт.** В `narrative_description` прозрачно покажи игроку весь расчет.
    *   **Формат для проверки навыка:** `Проверка [Навыка]: [Результат d20] + [Модификатор] = [Итог] против СЛ [Значение СЛ] -> Успех/Провал.`
    *   **Формат для атаки:** `Бросок атаки: [Результат d20] + [Модификатор] = [Итог] против КД [Значение КД] -> Попадание/Промах.`

4.  **Симуляция других "бросков" (урон, эффекты).** Используй тот же принцип. Для урона 2d6 (диапазон 2-12), выбери результат в зависимости от успеха атаки: слабый удар (2-4), средний (5-8), мощный/критический (9-12). Всегда показывай расчет.
    *   **Формат для урона:** `Урон: <span class="damage">[результат броска] ([формула кубиков])</span>`

5.  **Опиши результат.** После всех расчетов дай яркое и логичное описание последствий. Каждое механическое последствие (урон, исцеление, потраченный предмет) ДОЛЖНО быть отражено в `structural_changes`.
</RULES>

<OUTPUT_FORMAT>
Твой ответ ДОЛЖЕН быть ОДНИМ JSON-объектом, БЕЗ каких-либо дополнительных пояснений или текста до/после него. JSON должен строго соответствовать Pydantic-модели `ActionOutcome`.
-   `narrative_description`: Красочное описание для игрока. **ОБЯЗАТЕЛЬНО** используй эти HTML-теги:
    -   `<span class="name">Имя</span>` для имен и названий.
    -   `<span class="damage">описание урона</span>` для любого вреда.
    -   `<span class="heal">описание исцеления</span>` для восстановления здоровья.
    -   `<span class="condition">описание сосстояния</span>` для наложения эффектов.
-   `structural_changes`: Список объектов, описывающих конкретные изменения. Также используй теги. Обязательно указывай числа и результаты бросков, а не сами броски. Если изменений нет, оставь пустым `[]`.
-   `is_legal`: `true` или `false`.

**Примеры:**
- **Действие:** "Я атакую гоблина своим мечом."
  - **Результат:** `narrative_description` содержит бросок атаки, урон. `structural_changes` содержит изменение `current_hp` гоблина.
- **Действие:** "Я пью зелье лечения."
  - **Результат:** `narrative_description` описывает, как персонаж пьет зелье и чувствует себя лучше. `structural_changes` содержит изменение `current_hp` персонажа и удаление зелья из инвентаря.
- **Действие:** "Я пытаюсь убедить стражника пропустить меня."
  - **Результат:** `narrative_description` содержит проверку навыка Убеждения и реакцию стражника. `structural_changes` может быть пустым, если стражник не меняет своего мнения.
</OUTPUT_FORMAT>

<CONTEXT>
{chapter.get_actual_context()}
</CONTEXT>

<TASK>
Персонаж <span class="name">{character.name}</span> совершает следующее действие: "{action_text}"
{"IMPORTANT: the current character is an NPC so you should make corresponding narrative" if is_NPC else ""}
Сгенерируй JSON-объект `ActionOutcome`, описывающий результат.
</TASK>
"""
    
    def get_turn_analysis_prompt(self, chapter: 'Chapter', current_mode) -> str: # current_mode: GameModeDecision
        """
        Generates a prompt for the LLM to act as a Game Director, analyzing
        if the game state should switch between COMBAT and NARRATIVE modes.
        """
        return f"""
<SYSTEM>
{global_defines.dungeon_master_core_prompt}
</SYSTEM>

<ROLE>
Ты — Режиссёр Игры (Game Director). Твоя задача — не описывать события, а анализировать игровой процесс на мета-уровне. Ты должен определить, в каком режиме должна продолжаться игра: в пошаговом бою (`COMBAT`) или в свободном повествовании (`NARRATIVE`).
</ROLE>

<GOAL>
Проанализируй последнее действие и текущую ситуацию в игре, чтобы вынести вердикт о смене или сохранении игрового режима. Твой вывод поможет системе управлять игровым циклом.
</GOAL>

<DEFINITIONS>
- **`COMBAT` (Боевой режим):** Структурированный, пошаговый режим. Используется, когда начались активные боевые действия. Время течет дискретно (раунд за раундом). Персонажи совершают действия по очереди.
- **`NARRATIVE` (Повествовательный режим):** Свободный режим. Используется для диалогов, исследований, путешествий и решения головоломок. Время течет плавно, и персонажи могут действовать свободно, без строгой очередности.
</DEFINITIONS>

<HEURISTICS_FOR_DECISION>
Используй эти правила для принятия решения:

1.  **Переход в `COMBAT`:**
    *   **Главный триггер:** Персонаж совершил враждебное действие (атаковал, использовал вредоносное заклинание даже если оно не причинило вреда врагу).
    *   **Другие триггеры:** NPC явно объявил о своем намерении атаковать; сработала ловушка, нанеся урон; началась внезапная атака на персонажей.
    *   **Пример:** Если персонаж в тронном зале выхватывает меч и атакует стражника, режим **НЕМЕДЛЕННО** должен стать `COMBAT` даже если пока никто не был атакован.
    *   **Замечание:** Ели игроки начинают атаковать друг друга, режим должен стать `COMBAT` до тех пор пока они не договорятся о прекращении боя. 
    *   **Важно:** Любое агрессивное действие, даже если оно не приводит к урону, должно переключать режим на `COMBAT`. 
2.  **Переход в `NARRATIVE`:**
    *   **Главный триггер:** Последний враг в бою побежден, сдался или сбежал.
    *   **Другие триггеры:** Напряженная ситуация разрешилась мирным путем (успешное убеждение, обман); персонажи успешно скрылись от угрозы; бой окончен, и игроки хотят обыскать тела или исследовать локацию.
    *   **Пример:** Если персонажи победили всех гоблинов в комнате, режим должен переключиться на `NARRATIVE`, чтобы они могли спокойно собрать добычу.

3.  **Сохранение текущего режима:**
    *   Если игра в режиме `COMBAT` и персонаж просто атакует следующего врага, режим остается `COMBAT`.
    *   Если игра в режиме `NARRATIVE` и п��рсонаж просто продолжает диалог или исследует комнату, режим остается `NARRATIVE`.
</HEURISTICS_FOR_DECISION>

<OUTPUT_FORMAT>
Твой ответ ДОЛЖЕН быть ОДНИМ JSON-объектом, БЕЗ каких-либо дополнительных пояснений или текста до/после него. JSON должен строго соответствовать Pydantic-модели `TurnAnalysisOutcome`.
-   `recommended_mode`: `COMBAT` или `NARRATIVE`.
-   `analysis_summary`: Краткое и чёткое объяснение твоего выбора на русском языке. Почему ты рекомендуешь именно этот режим?
</OUTPUT_FORMAT>

<CONTEXT>
- **Текущий режим игры:** `{current_mode.new_mode}`
- **Общая обстановка:** {chapter.get_actual_context()}
</CONTEXT>

<TASK>
Проанализируй предоставленный контекст и сгенерируй JSON-объект `TurnAnalysisOutcome`.
</TASK>
"""

    def get_story_progression_prompt(self, story_manager: 'StoryManager', context: str) -> str:
        """
        Generates a prompt for the LLM to determine if the story's completion conditions have been met.
        """
        current_plot_point = story_manager.get_current_plot_point()
        if not current_plot_point:
            raise ValueError("No current plot point found.")
            # return "" # Should not happen if called correctly

        return f"""
<ROLE>
You are a Story Progression Engine. Your task is to analyze the recent events in the game and determine if the players have successfully met the completion conditions for the current chapter of the story.
</ROLE>

<GOAL>
Based on the provided context and completion conditions, you must decide if the story should advance to the next plot point.
</GOAL>

<STORY_CONTEXT>
The overarching goal of the campaign '{story_manager.story.title}' is: {story_manager.story.main_goal}.
The current active chapter of the story is '{current_plot_point.title}'.
The objective for this chapter is: {current_plot_point.description}.
</STORY_CONTEXT>

<COMPLETION_CONDITIONS>
To advance the story, the players need to achieve this: "{current_plot_point.completion_conditions}"
</COMPLETION_CONDITIONS>

<RECENT_EVENTS>
{context}
</RECENT_EVENTS>

<TASK>
Analyze the <RECENT_EVENTS> and determine if they satisfy the <COMPLETION_CONDITIONS>.
Your response must be ONLY a valid JSON object that conforms to the `StoryProgressionCheck` schema.
- Set `conditions_met` to `true` if the objective is complete.
- Set `conditions_met` to `false` if the objective is not yet complete.
- Provide a brief `reasoning` for your decision.
</TASK>
"""