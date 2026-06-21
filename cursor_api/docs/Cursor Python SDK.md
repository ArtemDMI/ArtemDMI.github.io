SDK
Cursor Python SDK
Пакет cursor-sdk позволяет вызывать Agent'а Cursor из собственного кода на Python. Того же Agent'а, который работает в Cursor IDE, CLI и веб-приложении, можно использовать из Python: доступны синхронные и асинхронные клиенты, типизированные датаклассы и обычная итерация по потокам и страницам. Запустите навык /sdk в Cursor, чтобы начать.

Сведения о REST API см. в разделе API облачных агентов.

Обзор
SDK объединяет локальные и облачные среды выполнения под единым интерфейсом. Вы пишете один и тот же код независимо от того, где запускается Agent.

Среда выполнения	Что делает	Когда использовать
Local	Запускает Agent'а на локальных файлах на диске.	Скрипты для разработки и проверки CI для рабочего дерева Git.
Cloud (Cursor-hosted)	Запускается в изолированной VM с клонированным репозиторием. VM управляются Cursor.	Когда у вызывающей стороны нет репозитория, нужно запускать много Agent'ов параллельно или запуски должны продолжаться даже после отключения вызывающей стороны.
Cloud (self-hosted)	Та же схема, но с использованием пула в собственной инфраструктуре.	По тем же причинам, что и для Cursor-hosted, а также когда код, секреты и артефакты сборки должны оставаться в вашей инфраструктуре.
Задайте среду выполнения, передав local или cloud в Agent.create().

Аутентификация
Задайте CURSOR_API_KEY или передайте api_key перед созданием Agent.

SDK принимает пользовательские API-ключи и API-ключи сервисных аккаунтов как для локальных, так и для облачных запусков. API-ключи Admin API команды пока не поддерживаются.

Пользовательский API-ключ из Cursor Dashboard -> API Keys
API-ключ сервисного аккаунта из настроек команды. См. Сервисные аккаунты

export CURSOR_API_KEY="your-key"
Использование и оплата
Для запусков SDK действуют те же тарифы, пулы запросов и правила режима конфиденциальности, что и для запусков из IDE и Cloud Agents. Затраты отображаются в дашборде использования вашей команды с тегом SDK.

Основные понятия
Понятие	Описание
Agent	Долговечный дескриптор, который хранит состояние диалога, конфигурацию рабочего пространства, выбор модели и настройки. Сохраняется между несколькими промптами.
Run	Одна отправка промпта. Имеет собственный поток событий, статус, результат, диалог и механизм отмены.
SDKMessage	Типизированное сообщение потока, выдаваемое во время выполнения. Имеет одинаковую структуру в локальных и облачных средах выполнения.
CursorClient	Явный клиент для управления жизненным циклом, пользовательских HTTP-параметров и работы с несколькими рабочими пространствами в одном процессе. Client — псевдоним.
AsyncClient	Async-клиент, зеркально повторяющий sync-версию. Требуется для всех async-операций.
Установка

pip install cursor-sdk
Требуется Python 3.10 или новее.

Быстрый старт

import os
from cursor_sdk import Agent, LocalAgentOptions
with Agent.create(
    model="composer-2.5",
    api_key="crsr_key",
    local=LocalAgentOptions(cwd=os.getcwd()),
) as agent:
    print(agent.send("Summarize what this repository does").text())
События потока показывают, как извлекать текст ассистента, обрабатывать вызовы инструментов и читать состояние запуска. Для одноразового промпта (создать, запустить, завершить) см. Agent.prompt().

Быстрый старт в Cloud
Python SDK имеет встроенную поддержку облачных агентов Cursor. Вы можете получить список подключенных репозиториев, запустить Agent'а для одного из них, дождаться завершения запуска и проверить итоговый результат.


from cursor_sdk import Agent, CloudAgentOptions, CloudRepository
with Agent.create(
    model="composer-2.5",
    api_key="crsr_key",
    cloud=CloudAgentOptions(
        repos=[CloudRepository(url="https://github.com/your-org/your-repo", starting_ref="main")],
        auto_create_pr=True,
    ),
) as agent:
    print(agent.send("Add structured logging to the auth middleware").text())
Облачные агенты, запущенные через SDK, исключаются из стандартного списка Agent'ов. Чтобы увидеть их в Cursor Web или в окне Agent'ов Cursor, нажмите Filter > Source > SDK.

Использование async
Async-клиент повторяет sync-интерфейс и рекомендуется для серверов, ботов и оркестрации нескольких Agent. AsyncAgent, AsyncClient, AsyncRun и AsyncCursor экспортируются как из cursor_sdk, так и из cursor_sdk.asyncio.


import asyncio
import os
from cursor_sdk import AsyncClient, LocalAgentOptions
async def main():
    async with await AsyncClient.launch_bridge(workspace=os.getcwd()) as client:
        async with await client.agents.create(
            model="composer-2.5",
            api_key="crsr_key",
            local=LocalAgentOptions(cwd=os.getcwd()),
        ) as agent:
            run = await agent.send("Summarize what this repository does")
            print(await run.text())
asyncio.run(main())
Глобального async-клиента по умолчанию не существует. Явно создайте AsyncClient или используйте AsyncClient.launch_bridge(...) как асинхронный контекстный менеджер, чтобы у каждого цикла событий был собственный клиент. Не смешивайте sync- и async-клиенты в одном и том же кодовом пути.

Синхронный	Асинхронный
CursorClient / Client	AsyncClient / AsyncCursorClient
Agent	AsyncAgent
Run	AsyncRun
Cursor	AsyncCursor
ListResult	AsyncListResult
DefaultHttpxClient	DefaultAsyncHttpxClient
Создание Agent'ов
Agent.create() проверяет параметры и сразу возвращает дескриптор. Передайте local или cloud, чтобы выбрать среду выполнения.


from cursor_sdk import Agent, CloudAgentOptions, CloudRepository, LocalAgentOptions
agent = Agent.create(
    model="composer-2.5",
    local=LocalAgentOptions(cwd="."),
)
cloud_agent = Agent.create(
    model="composer-2.5",
    cloud=CloudAgentOptions(
        repos=[CloudRepository(url="https://github.com/your-org/your-repo", starting_ref="main")],
        auto_create_pr=True,
    ),
)
Чтобы указать пул в собственной инфраструктуре, задайте env в CloudAgentOptions:


from cursor_sdk import CloudAgentOptions, CloudEnvironment, CloudRepository
cloud_agent = Agent.create(
    model="composer-2.5",
    cloud=CloudAgentOptions(
        env=CloudEnvironment(type="pool", name="acme-prod-pool"),
        repos=[CloudRepository(url="https://github.com/your-org/your-repo")],
    ),
)
agent.agent_id заполняется сразу. Локальные Agent'ы получают ID вида agent-<uuid>, а облачные агенты — вида bc-<uuid>. agent.model имеет тип ModelSelection, поэтому agent.model.id и agent.model.params можно использовать напрямую.

Облачные агенты, запущенные через SDK, не отображаются в списке Agent'ов по умолчанию. Чтобы увидеть их в Cursor Web или в окне Agent в Cursor, нажмите Filter > Source > SDK.

Переменные среды сессии
Для облачных Agent'ов передавайте env_vars, если запуску требуются временные учетные данные или другие значения, которые должны быть доступны только этому Agent'у.


agent = Agent.create(
    model="composer-2.5",
    cloud=CloudAgentOptions(
        repos=[CloudRepository(url="https://github.com/your-org/your-repo")],
        env_vars={
            "STAGING_API_TOKEN": os.environ["STAGING_API_TOKEN"],
        },
    ),
)
Эти значения шифруются при хранении, передаются в shell облачного Agent'а и удаляются вместе с Agent'ом. env_vars нельзя использовать с agent_id, переданным вызывающей стороной; не указывайте agent_id и считывайте сгенерированный сервером идентификатор из agent.agent_id. Имена переменных не могут начинаться с CURSOR_.

Параметры модели
Используйте ModelSelection.params, чтобы передавать параметры для конкретной модели, например reasoning effort или max mode. Идентификаторы и значения параметров зависят от модели. Используйте Cursor.models.list(), чтобы узнать, какие параметры и предустановленные варианты доступны для вашего аккаунта.


from cursor_sdk import Agent, LocalAgentOptions, ModelParameterValue, ModelSelection
agent = Agent.create(
    model=ModelSelection(
        id="composer-2.5",
        params=[ModelParameterValue(id="thinking", value="high")],
    ),
    local=LocalAgentOptions(cwd="."),
)
Используйте Cursor.models.list(), чтобы узнать идентификаторы параметров и предустановленные варианты для конкретной модели.

Необработанные словари
Типизированные датаклассы предпочтительны в коде приложения, так как в IDE лучше работают автодополнение и проверка типов. SDK также принимает обычные словари для коротких скриптов и JSON из внешних источников. Ключи в формате snake_case нормализуются.


from cursor_sdk import Agent
with Agent.create(
    {
        "api_key": "crsr_key",
        "model": {"id": "composer-2.5"},
        "local": {"cwd": "."},
    }
) as agent:
    ...
Agent
Дескриптор, возвращаемый методами Agent.create(), Agent.resume(), client.agents.create() и client.agents.resume().


class Agent:
    agent_id: str
    model: ModelSelection | None
    client: CursorClient
    def send(
        self,
        message: str | Mapping[str, Any] | UserMessage,
        options: SendOptions | Mapping[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> Run: ...
    def reload(self) -> None: ...
    def close(self) -> None: ...
    def list_messages(
        self, options: Mapping[str, Any] | None = None
    ) -> list[AgentMessage]: ...
    def list_artifacts(self) -> list[SDKArtifact]: ...
    def download_artifact(self, path: str) -> bytes: ...
    def archive(self, options: Mapping[str, Any] | None = None) -> None: ...
    def unarchive(self, options: Mapping[str, Any] | None = None) -> None: ...
    def delete(self, options: Mapping[str, Any] | None = None) -> None: ...
Участник	Описание
agent_id	Стабильный идентификатор Agent'а. agent-<uuid> для локального режима, bc-<uuid> для облака.
model	Текущая выбранная модель в типизированном виде. Обновляется после успешной отправки с переопределением модели.
send	Запускает новый запуск с указанным промптом. Возвращает дескриптор Run.
reload	Повторно считывает конфигурацию из файловой системы (хуки, MCP проекта, субагенты) без закрытия.
close	Закрывает Agent'а и освобождает ресурсы.
list_messages	Возвращает историю сообщений Agent'а.
list_artifacts	Возвращает список файлов, созданных Agent'ом (только в облаке; локально возвращает пустой список).
download_artifact	Скачивает файл по пути (только в облаке; локально вызывает исключение).
archive / unarchive / delete	Управляет жизненным циклом облачного Agent'а.
Используйте менеджер контекста для автоматической очистки:


with Agent.create(model="composer-2.5", local=LocalAgentOptions(cwd=".")) as agent:
    print(agent.send("Explain this repository").text())
Когда вы используете sync-хелперы Agent.* или Cursor.* без передачи client=, SDK запускает клиент по умолчанию уровня модуля или повторно использует уже существующий. Он автоматически закрывается при завершении процесса, и вы можете закрыть его явно:


from cursor_sdk import close_default_client
close_default_client()
Agent.prompt()

Agent.prompt(
    message: str | Mapping[str, Any] | UserMessage,
    options: AgentOptions | Mapping[str, Any] | None = None,
    *,
    client: CursorClient | None = None,
) -> RunResult
Удобство одноразового вызова: создает Agent, отправляет один запрос, дожидается завершения запуска и освобождает ресурсы.


from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
result = Agent.prompt(
    "What does the auth middleware do?",
    AgentOptions(model="composer-2.5", local=LocalAgentOptions(cwd=".")),
)
print(result.result)
Асинхронный вариант (предполагается, что у вас уже открыт AsyncClient):


from cursor_sdk import AgentOptions, AsyncAgent, LocalAgentOptions
result = await AsyncAgent.prompt(
    "What does the auth middleware do?",
    AgentOptions(model="composer-2.5", local=LocalAgentOptions(cwd=".")),
    client=client,
)
CursorClient
Используйте CursorClient, если вам нужен явный контроль над жизненным циклом, пользовательский endpoint bridge, пользовательские HTTP-параметры или несколько рабочих пространств в одном процессе. Client по-прежнему доступен как псевдоним.


from cursor_sdk import CursorClient, LocalAgentOptions
with CursorClient.launch_bridge(workspace=".") as client:
    with client.agents.create(
        model="composer-2.5",
        api_key="crsr_key",
        local=LocalAgentOptions(cwd="."),
    ) as agent:
        print(agent.send("Summarize what this repository does").text())
Ресурсы
Явные клиенты предоставляют пространства имён для ресурсов:

Ресурс	Примеры синхронных методов	Примеры асинхронных методов
agents	client.agents.create(...), client.agents.list(...), client.agents.get(...)	await client.agents.create(...), await client.agents.list(...)
models	client.models.list()	await client.models.list()
repositories	client.repositories.list()	await client.repositories.list()
Методы верхнего уровня, такие как client.create_agent(...) и client.list_agents(...), по-прежнему доступны, но для кода приложения предпочтительнее пространства имён ресурсов.

Пользовательские HTTP-клиенты
Клиенты sync и async поддерживают использование пользовательского клиента httpx для работы с прокси, транспортами и другими расширенными настройками HTTP:


from cursor_sdk import CursorClient, DefaultHttpxClient
with CursorClient.launch_bridge(
    workspace=".",
    http_client=DefaultHttpxClient(proxy="http://proxy.example.com"),
) as client:
    ...

from cursor_sdk import AsyncClient, DefaultAsyncHttpxClient
async with await AsyncClient.launch_bridge(
    workspace=".",
    http_client=DefaultAsyncHttpxClient(proxy="http://proxy.example.com"),
) as client:
    ...
DefaultHttpxClient и DefaultAsyncHttpxClient используют стандартные для SDK тайм-аут и поведение при перенаправлениях. Обычные httpx.Client и httpx.AsyncClient вместо этого используют настройки httpx по умолчанию.

Подключение к работающему bridge
Если у вас уже есть эндпоинт bridge (например, sidecar, которым управляет ваша платформа), используйте connect(...), чтобы подключиться без запуска нового процесса:


from cursor_sdk import CursorClient, LocalAgentOptions
with CursorClient.connect(
    base_url="http://127.0.0.1:8765",
    auth_token="bridge_token",
) as client:
    with client.agents.create(
        model="composer-2.5",
        api_key="crsr_key",
        local=LocalAgentOptions(cwd="."),
    ) as agent:
        ...
Асинхронный вариант использует AsyncClient.connect(...) и await client.aclose(). В обоих случаях по умолчанию задано allow_api_key_env_fallback=False; передавайте api_key= при каждом вызове или при создании клиента включите резервный режим с использованием переменной окружения.

Настройка таймаутов и повторных попыток
Оба клиента поддерживают with_options(...), который возвращает неглубокую копию с общими параметрами подключения и переопределёнными значениями по умолчанию:


short = client.with_options(timeout=5.0, max_retries=2)
agent = short.agents.create(model="composer-2.5", local=LocalAgentOptions(cwd="."))
Асинхронный вариант:


short_async = async_client.with_options(timeout=5.0, max_retries=2)
agent = await short_async.agents.create(model="composer-2.5", local=LocalAgentOptions(cwd="."))
Отправка сообщений
Каждый agent.send() возвращает Run. Каждый await async_agent.send() возвращает AsyncRun. Agent сохраняет контекст диалога между запусками; run — единица работы для одного промпта.


print(agent.send("Find the bug in src/auth.py").text())
# Тот же agent, полный контекст диалога сохраняется.
print(agent.send("Fix it and add a regression test").text())
Асинхронный вариант:


run = await agent.send("Find the bug in src/auth.py")
print(await run.text())
run = await agent.send("Fix it and add a regression test")
print(await run.text())
Чтобы отправлять изображения вместе с текстом:


run = agent.send(
    {
        "text": "What's in this screenshot?",
        "images": [{"data": base64_png, "mimeType": "image/png"}],
    }
)
Также можно использовать вспомогательные датаклассы. SDKImage.from_file(path) считывает данные с диска и кодирует их в base64:


from cursor_sdk import SDKImage, UserMessage
run = agent.send(
    UserMessage(
        text="What's in this screenshot?",
        images=[SDKImage.from_file("screenshot.png")],
    )
)
SDKImage.data_image(base64_data, mime_type) и SDKImage.url_image(url) также доступны для тех, у кого уже есть закодированные байты или удалённый URL.

Run

class Run:
    id: str
    agent_id: str
    status: str  # "running" | "finished" | "error" | "cancelled" | "expired"
    result: str
    model: ModelSelection | None
    duration_ms: int
    git: RunGitInfo | None
    created_at: str | None
    def messages(self) -> Iterator[SDKMessage]: ...
    def events(self) -> Iterator[RunStreamEvent]: ...
    def iter_text(self) -> Iterator[str]: ...
    def text(self) -> str: ...
    def wait(self) -> RunResult: ...
    def cancel(self) -> None: ...
    def conversation(self) -> list[ConversationTurn]: ...
    def conversation_json(self) -> str: ...
    def observe(self, *, after_offset: str | None = None) -> Iterator[RunStreamEvent]: ...
    def supports(self, operation: str) -> bool: ...
    def unsupported_reason(self, operation: str) -> str | None: ...
    def on_did_change_status(
        self, listener: Callable[[str], None]
    ) -> Callable[[], None]: ...
run.stream() — это псевдоним для run.messages(). При прямой итерации по run возвращаются оболочки RunStreamEvent, как и при вызове run.events().

AsyncRun предоставляет те же поля состояния. Методы, выполняющие I/O, являются асинхронными: async for message in run.messages(), async for event in run.events(), async for text in run.iter_text(), await run.text(), await run.wait(), await run.cancel(), await run.conversation(), await run.conversation_json() и async for event in run.observe().

Стриминг

run = agent.send("Find the bug in src/auth.py")
for message in run.messages():
    if message.type == "assistant":
        for block in message.message.content:
            if block.type == "text":
                print(block.text, end="")
    elif message.type == "thinking":
        print(message.text, end="")
    elif message.type == "tool_call":
        print(f"[tool] {message.name}: {message.status}")
    elif message.type == "status":
        print(f"[status] {message.status}")
Поток выполнения можно прочитать только один раз. run.messages(), run.events() и run.iter_text() используют один и тот же базовый поток и продвигают его. После завершения потока выполнение хранит итоговый результат (run.result, run.status, run.git, ...). Вызовите run.wait(), чтобы получить все оставшиеся события и вернуть типизированный RunResult.

Ожидание без стриминга

result = run.wait()
print(result.status)       # "finished" | "error" | "cancelled" | "expired"
print(result.result)       # final assistant text, if any
print(result.model)        # resolved ModelSelection used for this run
print(result.duration_ms)
print(result.git)          # RunGitInfo on cloud
Асинхронный вариант:


result = await run.wait()
Чтение текстовых выходных данных
iter_text() выдает текст ассистента по мере поступления. text() возвращает итоговый текст из терминала и ожидает wait(), если запуск все еще выполняется.


for chunk in run.iter_text():
    print(chunk, end="")
final_text = run.text()
Асинхронный вариант:


async for chunk in run.iter_text():
    print(chunk, end="")
final_text = await run.text()
Отмена выполнения

run.cancel()
Асинхронный вариант:


await run.cancel()
run.cancel() запрашивает отмену активного запуска. Статус меняется на "cancelled", поток в реальном времени останавливается, выполняющиеся вызовы инструментов прекращаются, а run.wait() возвращает status: "cancelled". Частичные выходные данные (текст ассистента, записанный к этому моменту) остаются в объекте Run.

Попытка отменить запуск, уже находящийся в конечном состоянии ("finished", "error", "cancelled", "expired"), вызывает UnsupportedRunOperationError. Если есть сомнения, проверяйте run.status:


if run.status == "running":
    run.cancel()
Получение состояния выполнения

print(run.id)
print(run.status)  # "running" | "finished" | "error" | "cancelled" | "expired"
stop = run.on_did_change_status(lambda status: print(f"status changed to {status}"))
stop()  # удалить слушатель
turns = run.conversation()
run.conversation() возвращает типизированный list[ConversationTurn]. Используйте его для отображения или сохранения структурированной истории без подписки на поток событий в реальном времени. run.conversation_json() возвращает JSON-строку в исходном виде.

Для асинхронных запусков используйте await run.conversation() и await run.conversation_json().

Переопределение модели для отдельного запуска
model, который вы передаёте в agent.send(), переопределяет выбранную Agent'ом модель для этого запуска, а затем закрепляется: последующие отправки без переопределения продолжают использовать новую модель. Чтобы переключиться обратно, передайте другое значение model или посмотрите текущий выбор в agent.model.


from cursor_sdk import ModelParameterValue, ModelSelection, SendOptions
run = agent.send(
    "Plan the refactor",
    SendOptions(
        model=ModelSelection(
            id="composer-2.5",
            params=[ModelParameterValue(id="thinking", value="high")],
        ),
    ),
)
run.model и result.model отражают выбор модели, использованный в этом запуске, и после начала запуска больше не изменяются.

Режим диалога
Передайте mode="plan" или mode="agent", чтобы определить, будет ли запуск сначала анализировать запрос и строить план или сразу вносить изменения. См. режим планирования, чтобы узнать, как этот режим работает в продукте.

Задайте mode в AgentOptions, передаваемом в Agent.create(), чтобы установить режим для первого запуска. В последующих вызовах agent.send() не указывайте mode, чтобы сохранить текущий режим диалога, или передайте mode, чтобы переключить режим только для этого запуска.


from cursor_sdk import Agent, AgentOptions, CloudAgentOptions, CloudRepository, SendOptions
with Agent.create(
    AgentOptions(
        model="composer-2.5",
        mode="plan",
        cloud=CloudAgentOptions(
            repos=[CloudRepository(url="https://github.com/your-org/your-repo")],
        ),
    )
) as agent:
    agent.send("Design the auth refactor").wait()
    agent.send(
        "Looks good, start building",
        SendOptions(mode="agent"),
    ).wait()
Стриминг необработанных дельт
Передайте колбэки on_delta и on_step в SendOptions, чтобы получать низкоуровневые обновления. Sync-колбэки вызываются непосредственно. Async-колбэки могут быть как sync, так и async; если они возвращают awaitable-значение, оно ожидается перед обработкой следующего события.


from cursor_sdk import SendOptions
def on_delta(update):
    if update.type in ("text-delta", "thinking-delta"):
        print(update.text, end="")
run = agent.send(
    "Refactor the utils module",
    SendOptions(on_delta=on_delta, on_step=lambda step: print(f"[step] {step.type}")),
)
run.wait()
Конкретные подклассы Update и Step находятся в cursor_sdk.events:


from cursor_sdk.events import TextDeltaUpdate, ToolCallStartedUpdate
if isinstance(update, TextDeltaUpdate):
    print(update.text)
Их по-прежнему можно импортировать из cursor_sdk для обратной совместимости, но в новом коде следует импортировать их из cursor_sdk.events.

SendOptions
Свойство	Тип	Описание
model	str | ModelSelection | Mapping[str, Any]	Переопределение модели для отдельной отправки. Если не указано, используется agent.model. Sticky: сохраняется после успешной отправки.
mode	"agent" | "plan"	Переопределение режима диалога для отдельной отправки. Если не указано в follow-up, сохраняется текущий режим диалога.
mcp_servers	Mapping[str, McpServerConfig]	Встроенные определения серверов MCP. Для этого запуска полностью заменяют серверы, заданные при создании.
local.force	bool	Только для локальных Agent'ов. По умолчанию — False. Принудительно завершает зависший активный запуск перед началом обработки этого сообщения. Cloud на стороне сервера возвращает 409 agent_busy, поэтому эквивалент не нужен.
idempotency_key	str	Необязательный ключ идемпотентности для отправки, сгенерированный клиентом.
on_step	Callable[[ConversationStep], Any]	Функция обратного вызова после каждого завершённого шага диалога (текст, размышление или пакет инструментов).
on_delta	Callable[[InteractionUpdate], Any]	Функция обратного вызова для каждого raw InteractionUpdate.
Следующие три раздела — это подробный справочник по SDKMessage, InteractionUpdate и ConversationTurn. При первом чтении их можно быстро просмотреть или пропустить; Возобновление работы агентов продолжает основное изложение.

События потока
run.messages() возвращает типизированные датаклассы сообщений SDK. Различайте их по message.type. Все сообщения включают agent_id и run_id, если runtime их предоставляет.


SDKMessage = (
    SDKSystemMessage
    | SDKUserMessageEvent
    | SDKAssistantMessage
    | SDKThinkingMessage
    | SDKToolUseMessage
    | SDKStatusMessage
    | SDKTaskMessage
    | SDKRequestMessage
    | Mapping[str, Any]
)
type	Dataclass	Ключевые поля
"system"	SDKSystemMessage	subtype, model, tools
"user"	SDKUserMessageEvent	message.content
"assistant"	SDKAssistantMessage	message.content со значениями TextBlock и ToolUseBlock
"thinking"	SDKThinkingMessage	text, thinking_duration_ms
"tool_call"	SDKToolUseMessage	call_id, name, status, args, result, truncated
"status"	SDKStatusMessage	status, message
"task"	SDKTaskMessage	status, text
"request"	SDKRequestMessage	request_id
SDKToolUseMessage возвращается дважды для большинства вызовов инструментов: сначала со status="running" и заполненным args, затем снова по завершении со status="completed" (или "error") и заполненным result. truncated указывает, сократил ли SDK args или result, потому что полезные данные были слишком большими.

Данные результата (итоговый текст, модель, длительность, git-метаданные) хранятся в объекте Run после завершения потока. Используйте run.wait(), чтобы получить их.

Схема tool_call нестабильна. Полезные данные args и result в событиях tool_call отражают внутреннюю структуру каждого инструмента и могут меняться по мере развития инструментов. Имена инструментов также могут быть переименованы или заменены. Считайте args и result нетипизированными данными и обрабатывайте их с учетом возможных изменений. Оболочка события (type, call_id, name, status) стабильна.

run.events() возвращает низкоуровневые оболочки RunStreamEvent. Используйте его, когда вам нужны смещения, оболочки итоговых результатов или необработанные обновления взаимодействия:


for event in run.events():
    print(event.kind, event.offset)
Обновления взаимодействия
InteractionUpdate — это raw-тип delta, передаваемый в callback on_delta метода agent.send(). Эти обновления более детализированы, чем события SDKMessage: текст поступает по токену, а вызовы инструментов отражают частичное состояние по мере накопления аргументов.


InteractionUpdate = (
    TextDeltaUpdate
    | ThinkingDeltaUpdate
    | ThinkingCompletedUpdate
    | ToolCallStartedUpdate
    | ToolCallCompletedUpdate
    | PartialToolCallUpdate
    | TokenDeltaUpdate
    | StepStartedUpdate
    | StepCompletedUpdate
    | TurnEndedUpdate
    | UserMessageAppendedUpdate
    | SummaryUpdate
    | SummaryStartedUpdate
    | SummaryCompletedUpdate
    | ShellOutputDeltaUpdate
    | UnknownInteractionUpdate
    | Mapping[str, Any]
)
PartialToolCallUpdate выдаётся, когда модель передаёт аргументы в вызов инструмента до commit. Здесь действует то же предупреждение о стабильности, что и для SDKToolUseMessage.args.

Типы диалога
Структурированное представление запуска по отдельным ходам, которое возвращает run.conversation(). Каждый элемент представляет собой обёртку, содержащую дискриминатор type хода и типизированную полезную нагрузку в turn.


@dataclass(frozen=True)
class ConversationTurn:
    type: str  # "agentConversationTurn" | "shellConversationTurn"
    turn: AgentConversationTurn | ShellConversationTurn | Mapping[str, Any]
@dataclass(frozen=True)
class AgentConversationTurn:
    user_message: Mapping[str, Any] | None = None
    steps: Sequence[ConversationStep] = ()
@dataclass(frozen=True)
class ShellConversationTurn:
    shell_command: ShellCommand | None = None
    shell_output: ShellOutput | None = None
ConversationStep = (
    AssistantConversationStep
    | ToolCallConversationStep
    | ThinkingConversationStep
    | Mapping[str, Any]
)
Различайте по turn.type и читайте данные через turn.turn:


for turn in run.conversation():
    if turn.type == "agentConversationTurn":
        for step in turn.turn.steps:
            print(step.type)
    elif turn.type == "shellConversationTurn":
        print(turn.turn.shell_command, turn.turn.shell_output)
run.conversation() из колбэков on_step срабатывает для каждого ConversationStep, а не для каждого хода. Шаги диалога с вызовом инструмента содержат payload типа Mapping[str, Any]. Считайте детали payload вызова инструмента нетипизированными данными; см. заметку о стабильности в разделе «События потока».

Возобновление работы агентов

Agent.resume(
    agent_id: str,
    options: AgentOptions | Mapping[str, Any] | None = None,
    *,
    client: CursorClient | None = None,
) -> Agent
Используйте Agent.resume() или client.agents.resume(), чтобы снова подключиться к существующему агенту по ID. Распространённые сценарии: повторное подключение к долго работающему облачному агенту, который был запущен ранее, или продолжение диалога после перезапуска локального процесса. Среда выполнения автоматически определяется по префиксу ID (bc- — облако, всё остальное — локально).


agent = Agent.resume("bc-abc123")
run = agent.send("Also update the changelog")
run.wait()
Асинхронный вариант:


agent = await client.agents.resume("bc-abc123")
run = await agent.send("Also update the changelog")
await run.wait()
agent.model будет None при resume, если вы не передадите model повторно. Inline MCP‑серверы не сохраняются после resume; они часто содержат секреты и существуют только в памяти. Передайте их повторно при resume или используйте file-based конфигурацию MCP (.cursor/mcp.json и local.setting_sources) для серверов, которые должны сохраняться.

Когда вы возобновляете облачный агент через мост, предоставленный вызывающей стороной (CursorClient.connect(...) или AsyncClient.connect(...)), SDK требует явно указать api_key, чтобы мост мог аутентифицировать последующие вызовы агента. Передайте его через AgentOptions:


from cursor_sdk import AgentOptions
agent = Agent.resume(
    "bc-abc123",
    AgentOptions(api_key="crsr_key"),
    client=client,
)
Локальное сохранение состояния
Локальные агенты сохраняют состояние диалога и метаданные запусков через bridge, поэтому последующие обращения и Agent.resume() работают даже после перезапуска процесса. По умолчанию bridge хранит эти данные на диске в корневом каталоге состояния для каждого рабочего пространства. Облачные агенты сохраняют состояние на стороне сервера, поэтому при возобновлении облачного агента из любого места вы получаете тот же диалог.

Локальное сохранение состояния привязано к рабочему пространству. Когда bridge работает как долгоживущий sidecar или подпроцесс, укажите для него то же рабочее пространство, что и у агента, чтобы локальные вызовы list, get и resume находили нужных агентов. Задайте это один раз в client и передавайте cwd в локальные вызовы list и get:


from cursor_sdk import CursorClient
with CursorClient.launch_bridge(workspace="/path/to/repo") as client:
    agents = client.agents.list(runtime="local", cwd="/path/to/repo")
    info = client.agents.get(agents.items[0].agent_id, cwd="/path/to/repo")
Просмотр агентов и запусков
Используйте CursorClient для API получения списка, получения и пагинации.


from cursor_sdk import CursorClient
with CursorClient.launch_bridge(workspace=".") as client:
    agents = client.agents.list(runtime="local", cwd=".")
    for agent_info in agents.auto_paging_iter():
        print(agent_info.agent_id)
    info = client.agents.get(agents.items[0].agent_id)
    runs = client.agents.list_runs(info.agent_id)
    run = client.agents.get_run(runs.items[0].id)
Асинхронный вариант:


agents = await client.agents.list(runtime="local", cwd=".")
async for agent_info in agents.auto_paging_iter():
    print(agent_info.agent_id)
info = await client.agents.get(agents.items[0].agent_id)
runs = await client.agents.list_runs(info.agent_id)
run = await client.agents.get_run(runs.items[0].id)
Используйте agent.list_messages() на дескрипторе агента, чтобы получить историю сообщений. Agent.messages.list(agent_id) — это удобный типизированный атрибут для того же вызова, когда у вас есть только ID.

Конечные точки List возвращают ListResult[T]. Используйте .items и .next_cursor напрямую, перебирайте элементы текущей страницы через for item in page или все страницы через .auto_paging_iter(). Асинхронные конечные точки List возвращают AsyncListResult[T]; async for item in page перебирает элементы текущей страницы, а async for item in page.auto_paging_iter() — все страницы в наборе результатов.

SDKAgentInfo
Структура метаданных, возвращаемая методами Agent.list(), Agent.get(), client.agents.list() и client.agents.get().


@dataclass(frozen=True)
class SDKAgentInfo:
    agent_id: str
    name: str
    summary: str
    last_modified: str | None = None
    status: str | None = None  # "running" | "finished" | "error"
    created_at: str | None = None
    archived: bool = False
    runtime: Literal["local", "cloud"] | None = None
    cwd: str = ""
    env: CloudEnvironment | None = None
    repos: Sequence[str] = ()
Жизненный цикл облачных Agent'ов
Облачные Agent'ы остаются в рабочем пространстве вашей команды, пока вы не архивируете или не удалите их. client.agents.list(runtime="cloud") по умолчанию скрывает архивированных Agent'ов; передайте include_archived=True, чтобы их увидеть. Отфильтруйте по pr_url, чтобы найти Agent'а, открывшего конкретный pull request.


# По ID, без дескриптора агента:
Agent.archive(agent_id)
Agent.unarchive(agent_id)
Agent.delete(agent_id)
# Через явный клиент:
client.agents.archive(agent_id)
client.agents.unarchive(agent_id)
client.agents.delete(agent_id)
# Через существующий дескриптор агента:
agent.archive()
agent.unarchive()
agent.delete()
archive выполняет мягкое удаление Agent'а, чтобы запись диалога оставалась доступной для чтения. unarchive восстанавливает его. delete удаляет безвозвратно; последующие попытки чтения возвращают NotFoundError.

Асинхронные методы жизненного цикла имеют те же имена, и их можно вызывать с await.

Пространство имён Cursor
Чтение данных на уровне аккаунта и каталога. Методы синхронизации принимают необязательный api_key, а в противном случае используют CURSOR_API_KEY.


from cursor_sdk import Cursor
me = Cursor.me()
models = Cursor.models.list()
repositories = Cursor.repositories.list()
Эквивалент с явно указанным клиентом:


me = client.me()
models = client.models.list()
repositories = client.repositories.list()
Асинхронный вариант:


from cursor_sdk import AsyncCursor
me = await AsyncCursor.me(client=client)
models = await AsyncCursor.models.list(client=client)
repositories = await AsyncCursor.repositories.list(client=client)
Используйте Cursor.models.list(), чтобы узнать корректные идентификаторы моделей и параметры каждой модели перед вызовом Agent.create() или agent.send(). Набор параметров зависит от модели. К распространённым примерам относятся reasoning effort и max mode.


models = Cursor.models.list()
composer = next((model for model in models if model.id == "composer-2.5"), None)
print(composer.parameters if composer else [])
# [
#   ModelParameterDefinition(
#       id="thinking",
#       display_name="Thinking",
#       values=(
#           ModelParameterDefinitionValue(value="low", display_name="Low"),
#           ModelParameterDefinitionValue(value="high", display_name="High"),
#       ),
#   ),
# ]
Предустановленные variants в каждом SDKModel уже содержат корректные params, поэтому вы можете скопировать их в ModelSelection.

Cursor.repositories.list() возвращает репозитории SCM (GitHub, GitLab, Bitbucket, Azure DevOps — в зависимости от того, что подключено), доступные для облачных агентов в аккаунте или команде, от имени которых выполняется вызов. Каждый элемент содержит url. Используйте их для заполнения CloudAgentOptions.repos.

MCP‑серверы
Агенты могут загружать MCP‑серверы из встроенных определений, настроек проекта и пользователя, плагинов и конфигурации, управляемой через дашборд, в зависимости от среды выполнения.


from cursor_sdk import (
    Agent,
    AgentOptions,
    HttpMcpServerConfig,
    LocalAgentOptions,
    McpAuth,
    StdioMcpServerConfig,
)
agent = Agent.create(
    AgentOptions(
        model="composer-2.5",
        local=LocalAgentOptions(cwd="."),
        mcp_servers={
            "docs": HttpMcpServerConfig(
                url="https://example.com/mcp",
                auth=McpAuth(client_id="client-id", scopes=["read", "write"]),
            ),
            "filesystem": StdioMcpServerConfig(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "."],
            ),
        },
    )
)
Плоские словари ({"type": "http", "url": ...} и {"type": "stdio", "command": ...}) также допускаются как удобный вариант для коротких скриптов.

Что загружается
Локальные Agent'ы загружают серверы максимум из пяти источников; при конфликте имен приоритет у первого совпадения:

mcp_servers в agent.send(). Полностью заменяет серверы, заданные при создании, для этого запуска (без объединения).
mcp_servers в Agent.create(). Используется, если для конкретного вызова send не задано переопределение.
Серверы плагинов, если local.setting_sources включает "plugins".
Серверы проекта из .cursor/mcp.json, если local.setting_sources включает "project".
Пользовательские серверы из ~/.cursor/mcp.json, если local.setting_sources включает "user".
Если local.setting_sources не задан, загружаются только inline‑серверы. Если локальный сервер MCP требует входа по OAuth, SDK может повторно использовать сохраненную авторизацию из приложения Cursor, но не может открыть браузер для входа.

Облачные Agent'ы загружают серверы из:

mcp_servers в agent.send(). Полностью заменяет серверы, заданные при создании, для этого запуска (без объединения).
mcp_servers в Agent.create(). Используется, если для конкретного вызова send не задано переопределение.
Ваших пользовательских и командных MCP‑серверов из cursor.com/agents.
Если inline‑сервер не содержит auth или headers, и вы ранее авторизовали URL этого сервера на cursor.com/agents, то запуски, аутентифицированные персональным API-токеном, автоматически повторно используют эти OAuth-токены. API-ключи сервисных аккаунтов не могут использовать пользовательскую аутентификацию как резервный вариант, так как не связаны с пользователем.

local.setting_sources не применяется к облачным Agent'ам.

Cloud
Облачный агент также поддерживает аутентифицированные конфигурации MCP, указанные inline. Cloud MCP поддерживает транспорты HTTP и stdio. Используйте HTTP headers для статических API-ключей или Bearer-токенов. Используйте HTTP auth для серверов, защищённых OAuth. Используйте stdio env, если сервер работает внутри облачной VM и считывает учётные данные из переменных среды.


from cursor_sdk import (
    Agent,
    AgentOptions,
    CloudAgentOptions,
    CloudRepository,
    HttpMcpServerConfig,
    StdioMcpServerConfig,
)
agent = Agent.create(
    AgentOptions(
        model="composer-2.5",
        cloud=CloudAgentOptions(
            repos=[CloudRepository(url="https://github.com/your-org/your-repo")],
        ),
        mcp_servers={
            "linear": HttpMcpServerConfig(
                url="https://mcp.linear.app/mcp",
                headers={"Authorization": "Bearer linear_pat_xxx"},
            ),
            "github": StdioMcpServerConfig(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_TOKEN": "ghp_xxx"},
            ),
        },
    )
)
HTTP headers и auth обрабатываются на бэкенде Cursor. Чувствительные поля маскируются и не попадают в VM.
Значения env для Stdio передаются в VM, потому что сервер работает там. Обращайтесь с ними как с любым другим секретом времени выполнения.
OAuth для MCP‑серверов, настроенных на cursor.com/agents, остается привязанным к пользователю даже для серверов на уровне команды.
См. MCP, чтобы узнать полный формат конфигурации, и возможности облачного агента — чтобы узнать об особенностях поведения в облаке.

Субагенты
Определите именованные субагенты, которые основной Agent может запускать с помощью инструмента Agent. Передавайте их прямо в коде:


from cursor_sdk import Agent, AgentDefinition, AgentOptions, LocalAgentOptions
agent = Agent.create(
    AgentOptions(
        model="composer-2.5",
        local=LocalAgentOptions(cwd="."),
        agents={
            "code-reviewer": AgentDefinition(
                description="Expert code reviewer for quality and security.",
                prompt="Review code for bugs, security issues, and proven approaches.",
                model="inherit",
            ),
            "test-writer": AgentDefinition(
                description="Writes tests for code changes.",
                prompt="Write comprehensive tests for the given code.",
            ),
        },
    )
)
Субагенты, добавленные в репозиторий по пути .cursor/agents/*.md (с фронтматтером name, description и необязательным model), также учитываются. Определения, заданные прямо в коде, переопределяют определения из файлов с тем же именем.

Вложенные субагенты
Субагенты могут создавать собственных субагентов в пределах ограничения по вложенности. Когда субагент использует инструмент Agent, он обращается к тому же механизму выполнения субагентов, что и родительский субагент, поэтому родительский субагент может делегировать задачу субагенту, который делегирует её дальше. На каждом уровне доступен один и тот же набор именованных субагентов. Верхнеуровневый агент и его прямые субагенты могут запускать субагентов, но субагент, запущенный другим субагентом, не может запускать новых.

Пользовательские инструменты
Пользовательские инструменты позволяют открывать локальным агентам доступ к функциям Python без развертывания отдельного сервера MCP. Передавайте их через LocalAgentOptions.custom_tools.


from cursor_sdk import Agent, CustomTool, CustomToolContext, LocalAgentOptions
def get_deployment_status(args, context: CustomToolContext):
    service = args["service"]
    return f"Service {service} is healthy."
with Agent.create(
    model="composer-2.5",
    local=LocalAgentOptions(
        cwd=".",
        custom_tools={
            "get_deployment_status": CustomTool(
                description="Look up the current deployment status for a service.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "service": {"type": "string", "description": "Service name"},
                    },
                    "required": ["service"],
                },
                execute=get_deployment_status,
            ),
        },
    ),
) as agent:
    agent.send("Is the checkout service healthy?").wait()
execute получает разобранные аргументы и CustomToolContext с tool_call_id, если он доступен. Он может возвращать строку, значение, совместимое с JSON, или словарь со списком content. Пользовательские инструменты доступны только для локальных агентов.

Хуки
Хуки поддерживаются только в файловом виде. Программного callback для хуков нет. Хуки — это граница политики проекта, а не параметр для отдельного запуска.

Локально: Добавьте .cursor/hooks.json в репозиторий, переданный как local.cwd, или добавьте ~/.cursor/hooks.json для пользовательских хуков.
Облачный: Закоммитьте .cursor/hooks.json и связанные с ним скрипты в репозиторий, переданный в cloud.repos. Облачные агенты, созданные через SDK, автоматически загружают хуки проекта. На тарифах Enterprise они также запускают хуки команды и хуки, централизованно управляемые в Enterprise.
См. Hooks — о формате конфигурации, а поддержка хуков в облачных Agents — о поведении в облачной среде.

Артефакты
Просматривайте список файлов и скачивайте их из рабочего пространства Agent.


@dataclass(frozen=True)
class SDKArtifact:
    path: str
    size_bytes: int = 0
    updated_at: str = ""

from pathlib import Path
artifacts = agent.list_artifacts()
for artifact in artifacts:
    print(artifact.path, artifact.size_bytes)
# Скачать один артефакт на диск.
content = agent.download_artifact(artifacts[0].path)
Path("review.md").write_bytes(content)
Асинхронные агенты поддерживают await agent.list_artifacts() и await agent.download_artifact(path).

Поддержка артефактов зависит от среды выполнения. Локальные агенты SDK возвращают пустой список из list_artifacts(), а при вызове download_artifact() возникает исключение.

Управление ресурсами
Всегда закрывайте агентов, когда закончите работу. Самый удобный синхронный вариант — использовать контекстный менеджер:


from cursor_sdk import Agent, LocalAgentOptions
with Agent.create(model="composer-2.5", local=LocalAgentOptions(cwd=".")) as agent:
    agent.send("Summarize the repository").wait()
Для явного освобождения:


agent.close()
Асинхронные агенты и клиенты поддерживают асинхронные менеджеры контекста и очистку ресурсов через await:


from cursor_sdk import AsyncClient, LocalAgentOptions
async with await AsyncClient.launch_bridge(workspace=".") as client:
    async with await client.agents.create(
        model="composer-2.5",
        local=LocalAgentOptions(cwd="."),
    ) as agent:
        run = await agent.send("Summarize the repository")
        await run.wait()
Для явного освобождения:


await agent.close()
await client.aclose()
Синхронный клиент по умолчанию на уровне модуля автоматически закрывается при завершении процесса. В долгоживущих процессах его можно явно закрыть и сбросить:


from cursor_sdk import close_default_client
close_default_client()
Справочник по конфигурации
Python SDK принимает вспомогательные дата-классы и raw-словари. В дата-классах используются поля Python в формате snake_case, и они предпочтительны для кода приложения.

AgentOptions
Свойство	Тип	По умолчанию	Описание
model	str | ModelSelection | Mapping[str, Any]	Обязательно для local; для cloud используется определенное сервером значение по умолчанию	Модель для использования. См. ModelSelection.
api_key	str	переменная окружения CURSOR_API_KEY	API-ключ пользователя или ключ сервисного аккаунта. Ключи администратора команды пока не поддерживаются.
name	str	Создается автоматически	Удобочитаемое имя агента, отображаемое в client.agents.list() / client.agents.get().
local	LocalAgentOptions | Mapping[str, Any]	None	Конфигурация локального агента. Укажите, чтобы создать локального агента.
cloud	CloudAgentOptions | Mapping[str, Any]	None	Конфигурация облачного агента. Укажите, чтобы создать облачного агента.
mcp_servers	Mapping[str, McpServerConfig]	None	Определения MCP‑серверов, заданные inline.
agents	Mapping[str, AgentDefinition | Mapping[str, Any]]	None	Определения субагентов.
agent_id	str	Создается автоматически	Постоянный ID агента. Укажите, чтобы сохранить стабильный ID между вызовами.
idempotency_key	str	Для cloud создается автоматически	Необязательный ключ идемпотентности, созданный клиентом. Только для cloud.
mode	"agent" | "plan"	"agent"	Начальный режим диалога для первого запуска агента. См. режим диалога.
LocalAgentOptions
Свойство	Тип	По умолчанию	Описание
cwd	str | os.PathLike | Sequence[str | os.PathLike]	None	Путь или пути рабочего пространства.
setting_sources	Sequence[SettingSource]	None	Слои настроек окружения: "project", "user", "team", "mdm", "plugins" или "all".
sandbox_options	SandboxOptions | Mapping[str, Any]	None	Параметры локальной песочницы.
store	LocalAgentStoreConfig | Mapping[str, Any]	None	Конфигурация локального хранилища, передаваемая в bridge.
auto_review	bool	None	Направлять локальные вызовы инструментов через Auto-review, если это поддерживает подключенный backend.
custom_tools	Mapping[str, CustomTool | Mapping[str, Any]]	None	Пользовательские инструменты, доступные локальным агентам.
CloudAgentOptions
Свойство	Тип	По умолчанию	Описание
env	CloudEnvironment | Mapping[str, Any]	{ type: "cloud" }	Среда выполнения. cloud использует виртуальные машины под управлением Cursor; pool и machine используют пул в собственной инфраструктуре.
repos	Sequence[CloudRepository | Mapping[str, Any]]	None	Репозитории для клонирования в виртуальную машину. Не указывайте repos и оставьте env со значением по умолчанию, чтобы использовать Agent без репозитория с пустым рабочим пространством. Передайте pr_url для репозитория, чтобы прикрепить Agent к существующему PR.
work_on_current_branch	bool	False	Отправлять коммиты в существующую ветку вместо создания новой.
auto_create_pr	bool	False	Открывать PR после завершения выполнения.
skip_reviewer_request	bool	False	Не запрашивать добавление вызывающего пользователя в ревьюеры PR.
env_vars	Mapping[str, str]	None	Переменные среды в рамках сессии для облачных агентов.
AgentDefinition
Свойство	Тип	По умолчанию	Описание
description	str	обязательно	Когда использовать этот субагент. Показывается родительскому Agentу, чтобы он знал, когда его запускать.
prompt	str	обязательно	Системный промпт для субагента.
model	str | ModelSelection | Mapping[str, Any] | "inherit"	"inherit"	Переопределение модели. Передайте "inherit", чтобы использовать выбор модели родительского Agentа.
mcp_servers	Sequence[str | AgentDefinitionMcpServer | Mapping[str, Any]]	None	MCP‑серверы, доступные для этого субагента. Имена ссылаются на серверы из mcp_servers родительского Agentа.
CustomTool

@dataclass
class CustomTool:
    execute: Callable[[Mapping[str, Any], CustomToolContext], Any]
    description: str | None = None
    input_schema: Mapping[str, Any] | None = None
class CustomToolContext:
    tool_call_id: str | None = None
ModelSelection

@dataclass(frozen=True)
class ModelSelection:
    id: str
    params: Sequence[ModelParameterValue] = ()
@dataclass(frozen=True)
class ModelParameterValue:
    id: str
    value: str
id — это идентификатор модели (например, "composer-2.5"). params содержит параметры конкретной модели, например reasoning effort. Используйте Cursor.models.list(), чтобы узнать допустимые идентификаторы, описания параметров и предустановленные варианты для вашего аккаунта.

McpServerConfig

McpServerConfig = (
    HttpMcpServerConfig
    | SseMcpServerConfig
    | StdioMcpServerConfig
    | Mapping[str, Any]
)
@dataclass(frozen=True)
class HttpMcpServerConfig:
    url: str
    type: Literal["http", "sse"] | str = "http"
    headers: Mapping[str, str] | None = None
    auth: McpAuth | Mapping[str, Any] | None = None
@dataclass(frozen=True)
class SseMcpServerConfig(HttpMcpServerConfig):
    type: Literal["sse"] = "sse"
@dataclass(frozen=True)
class StdioMcpServerConfig:
    command: str
    args: Sequence[str] | None = None
    env: Mapping[str, str] | None = None
    cwd: str | os.PathLike | None = None  # только локально; облако отклоняет это поле
@dataclass(frozen=True)
class McpAuth:
    client_id: str
    client_secret: str | None = None
    scopes: Sequence[str] = ()
Для HTTP-серверов, работающих в облаке, headers и auth обрабатываются бэкендом Cursor. Конфиденциальные поля скрываются до того, как их увидит VM. Для stdio-серверов в облаке значения env передаются в VM (обращайтесь с ними как с любым секретом среды выполнения).

UserMessage

@dataclass(frozen=True)
class UserMessage:
    text: str
    images: Sequence[SDKImage | Mapping[str, Any]] | None = None
Структурированная форма аргумента message метода agent.send(). Используйте её, чтобы отправлять изображения вместе с текстом.

SDKImage

@dataclass(frozen=True)
class SDKImage:
    url: str | None = None
    data: str | None = None
    mime_type: str | None = None
    dimension: SDKImageDimension | Mapping[str, Any] | None = None
    @classmethod
    def from_url(cls, url: str, dimension=None) -> SDKImage: ...
    @classmethod
    def from_data(cls, data: bytes | str, mime_type: str, dimension=None) -> SDKImage: ...
    @classmethod
    def url_image(cls, url: str, dimension=None) -> SDKImage: ...
    @classmethod
    def data_image(cls, data: str, mime_type: str, dimension=None) -> SDKImage: ...
    @classmethod
    def from_file(cls, path, *, mime_type=None, dimension=None) -> SDKImage: ...
Передайте либо удалённый url, либо данные data в формате base64 вместе с mime_type. from_data() принимает байты или строку в формате base64. from_file() считывает файл с диска и кодирует его в base64.

SettingSource

SettingSource = Literal["project", "user", "team", "mdm", "plugins", "all"]
Определяет, какие слои настроек, хранящиеся на диске, загружает локальный Agent. Облачные Agentы всегда загружают project, team и plugins и игнорируют это поле.

Значение	Источник
"project"	.cursor/ в рабочем пространстве
"user"	~/.cursor/
"team"	Настройки команды, синхронизированные с дашборда
"mdm"	Корпоративные настройки под управлением MDM
"plugins"	Настройки, предоставляемые плагинами
"all"	Краткая запись для всего перечисленного выше
ListResult

@dataclass(frozen=True)
class ListResult(Generic[T]):
    items: list[T]
    next_cursor: str = ""
    def to_dict(self) -> dict[str, Any]: ...
    def has_next_page(self) -> bool: ...
    def next_page_info(self) -> dict[str, str]: ...
    def get_next_page(self) -> ListResult[T]: ...
    def auto_paging_iter(self) -> Iterator[T]: ...
Возвращается методами client.agents.list(), client.agents.list_runs() и Agent.list(). next_cursor пуст, если страниц больше нет. Асинхронные эквиваленты конечных точек списка возвращают AsyncListResult[T] с awaitable-эквивалентами.

Ошибки
Все ошибки SDK наследуются от CursorAgentError. CursorSDKError — это обратносовместимый корневой псевдоним для прежнего кода. Используйте is_retryable и retry_after, чтобы управлять логикой повторных попыток.


class CursorAgentError(Exception):
    message: str
    code: str | None
    status: int | None
    status_code: int | None
    details: list[Mapping[str, Any]]
    is_retryable: bool
    cause: BaseException | None
    request_id: str | None
    headers: Mapping[str, str]
    retry_after: str | None
Ошибка	Когда
AuthenticationError	Недействительный API-ключ или вход не выполнен.
PermissionDeniedError	У аутентифицированного инициатора запроса нет прав на запрошенную операцию.
RateLimitError	Слишком много запросов или превышены лимиты использования.
ConfigurationError	Недопустимая модель, отсутствует обязательная конфигурация или некорректные параметры запроса.
AgentBusyError	Отправка follow-up, когда у агента уже есть запуск в состоянии CREATING или RUNNING (HTTP 409, код agent_busy).
BadRequestError	Запрос сформирован некорректно.
IntegrationNotConnectedError	При создании облачного агента для репозитория, SCM-провайдер которого не подключён.
NetworkError	Сервис недоступен или произошёл сбой сети.
APITimeoutError	Превышено время ожидания запроса.
InternalServerError	Сервис Cursor вернул серверную ошибку.
NotFoundError	Запрошенный ресурс не найден.
UnknownAgentError	Agent не найден или его не удаётся прочитать.
UnsupportedRunOperationError	Операция Run не поддерживается в текущем состоянии запуска.
Повторные попытки с увеличением задержки
is_retryable и retry_after определяют логику повторных попыток на стороне вызывающего кода. retry_after — это строка в формате HTTP (секунды или HTTP-дата), которую передаёт сервер, если она задана.


import time
from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions, RateLimitError
for attempt in range(3):
    try:
        result = Agent.prompt(
            "Audit the auth middleware for missing input validation",
            AgentOptions(model="composer-2.5", local=LocalAgentOptions(cwd=".")),
        )
        break
    except RateLimitError as err:
        time.sleep(float(err.retry_after) if err.retry_after else 2**attempt)
    except CursorAgentError as err:
        if not err.is_retryable:
            raise
        time.sleep(2**attempt)
Каждая ошибка CursorAgentError включает request_id, если сервер его вернул. Записывайте его в лог всякий раз, когда выводите ошибку, чтобы служба поддержки могла разобраться со сбоем.

IntegrationNotConnectedError

class IntegrationNotConnectedError(ConfigurationError):
    provider: str   # например "github", "gitlab", "azuredevops"
    help_url: str   # ссылка на дашборд для повторного подключения
Используйте help_url, чтобы направить пользователя к нужному сценарию повторного подключения. Новые провайдеры могут добавляться без выпуска новой версии SDK.

AgentBusyError
Облачные Agent поддерживают только один активный запуск одновременно. AgentBusyError возникает, если вы вызываете agent.send() (или иным образом создаете запуск), пока другой запуск того же Agent все еще находится в состоянии CREATING или RUNNING.

is_retryable имеет значение False. Если повторить попытку сразу, ошибка будет возникать снова, пока активный запуск не перейдет в конечное состояние или вы его не отмените. Другие ответы 409, например agent_archived, вместо этого вызывают ConfigurationError.

Дождитесь завершения активного запуска, отмените его с помощью run.cancel() или опрашивайте Agent.list_runs() перед следующей отправкой:


from cursor_sdk import Agent, AgentBusyError
agent = Agent.resume("bc-00000000-0000-0000-0000-000000000001")
try:
    agent.send("Also add tests for the auth middleware.")
except AgentBusyError:
    runs = Agent.list_runs(agent.agent_id, runtime="cloud", limit=1)
    active = runs.items[0] if runs.items else None
    if active is not None and active.status == "running":
        active.cancel()
    agent.send("Also add tests for the auth middleware.")
Локальные Agent не вызывают исключение AgentBusyError. Передайте local={"force": True} в вызов send(), чтобы завершить зависший локальный запуск перед запуском нового.

UnsupportedRunOperationError

class UnsupportedRunOperationError(ConfigurationError):
    operation: str
Возникает, если операция Run не разрешена для текущего запуска. Самый распространённый случай — run.cancel() для запуска, который уже находится в конечном состоянии.

run.supports(operation) и run.unsupported_reason(operation) сообщают, поддерживается ли операция на уровне SDK для имени операции ("stream", "wait", "cancel", "conversation"), и не проверяют состояние запуска. Чтобы защититься от вызовов, зависящих от состояния, проверяйте run.status.

Устранение неполадок
Задайте CURSOR_SDK_LOG=debug (или info), чтобы прикрепить обработчик stderr к собственному логгеру SDK. SDK настраивает только собственный логгер cursor_sdk, поэтому это не повлияет на логирование хост-приложения.


CURSOR_SDK_LOG=debug python my_script.py
Бинарный файл bridge из комплекта устанавливается в PATH под именем cursor-sdk-bridge вместе с пакетом. Запустите его напрямую, чтобы убедиться, что вместе с вашим wheel поставляется нужная сборка:


cursor-sdk-bridge --help
Известные ограничения
Схемы payload для вызовов инструментов намеренно не имеют строгой типизации.
Inline MCP‑сервер не сохраняются между вызовами Agent.resume(). При необходимости передайте их снова при возобновлении.
Пользовательские инструменты (local.custom_tools) поддерживаются только локальными Agentами.
Скачивание артефактов не реализовано для локальных Agentов.
local.setting_sources (и file-based пути MCP и субагент, которые он включает) не применяется к облачным агентам. Облачный режим всегда загружает project, team и plugins.
Хуки поддерживаются только через файл (.cursor/hooks.json). Программных callback нет.



Русский