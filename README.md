# AI Agents Creator

Framework leggero in Python per costruire **agenti AI specializzati** basati sull'
SDK di Claude (Anthropic), ispirato al modello dei *subagent* di Claude Code.

Caratteristiche principali:

- **Provider switch via `.env`**: stesso codice, usa **API Anthropic**, **AWS
  Bedrock** o **Google Cloud Vertex AI** cambiando una variabile d'ambiente.
- **Agenti + Orchestrator**: definisci agenti specializzati (prompt, tool,
  modello) e lascia che un orchestrator li coordini per eseguire un task.
- **Tool MCP**: gli agenti possono usare tool esposti da server MCP (Model
  Context Protocol) locali o remoti.
- **Protocollo A2A** (Agent-to-Agent): i tuoi agenti possono essere **chiamati
  da** agenti esterni e **chiamare** agenti esterni via HTTP JSON.
- **Trigger**: esegui gli agenti via **CLI**, **webhook HTTP** (FastAPI) o
  scheduler.
- **Due use case pronti** (vedi [examples/AGENTS.md](examples/AGENTS.md) per la
  lista completa degli agenti):
  1. *Knowledge Base builder*: legge contenuti da una cartella locale e li
     trasforma in knowledge base `.md` categorizzata con `INDEX.md`.
  2. *Editorial Calendar*: legge la stessa KB (solo i `.md` rilevanti tramite
     l'indice) e produce un calendario editoriale per i social.

> Vuoi creare un nuovo agente? Leggi [CLAUDE.md](CLAUDE.md) — guida operativa
> step-by-step per agenti in-process e/o esposti via A2A.

---

## Struttura del repo

```
src/ai_agents_creator/
├── config.py                # Settings da .env (provider, modelli, path, ecc.)
├── providers/               # Anthropic API / AWS Bedrock / Vertex AI
├── core/                    # Agent, Tool, Orchestrator, Registry
├── mcp/                     # Client MCP per tool esterni
├── a2a/                     # Server + client A2A (HTTP JSON)
├── triggers/                # Webhook FastAPI, CLI
└── agents/
    ├── _helpers.py          # standalone_app(agent) -> FastAPI per microservizio
    ├── knowledge_base/      # use case 1
    └── editorial_calendar/  # use case 2
examples/                    # Script eseguibili + AGENTS.md (catalogo agenti)
data/                        # Input e KB generata
```

---

## Architettura tecnica degli agenti

Questa sezione spiega **come** sono costruiti gli agenti e come si tengono
insieme i pezzi (LLM, tool, loop, orchestrator, A2A, MCP).

### 1. `Agent` = prompt + tool + mini-loop agentic

Un agente è un'istanza di `core.agent.Agent`. Ha:

- `name`, `description`, `system_prompt`
- una lista di `tools` (oggetti `core.tools.Tool`)
- parametri opzionali `model`, `max_tokens`, `temperature`, `max_iterations`

Il metodo `Agent.run(user_input)` implementa un **mini-loop agentic** che
ricalca il pattern *subagent* di Claude Code (vedi [src/ai_agents_creator/core/agent.py](src/ai_agents_creator/core/agent.py)):

```
1. costruisce messages = [{"role": "user", "content": user_input}]
2. ripete fino a max_iterations:
   a. chiama il modello via providers.factory.complete(...)
      passando system, messages, tools (formato Anthropic tool-use)
   b. accumula la risposta come messaggio "assistant"
   c. se NON ci sono blocchi `tool_use` -> estrae il testo finale, esce
   d. se ci sono `tool_use`:
      - per ogni tool_use trova il Tool corrispondente per nome
      - esegue tool.run(**input), serializza l'output a stringa
      - aggiunge un messaggio "user" con `tool_result` per ogni chiamata
      - torna al passo (a)
3. restituisce un AgentResult con output_text, messages, tool_calls, stop_reason
```

Il modello stesso decide quando smettere di chiamare tool e produrre testo.
Errori dei tool vengono inseriti nel `tool_result` con `is_error=True`, così
l'LLM può eventualmente recuperare.

### 2. `Tool` = funzione Python con schema JSON

`core.tools.Tool` wrappa una funzione Python in un formato che l'API Anthropic
capisce (`name`, `description`, `input_schema` in JSON Schema). Esistono due
modi per dichiarare un tool:

```python
from ai_agents_creator.core.tools import Tool, tool

# 1) Decorator: schema inferito dalla signature
@tool(description="Somma due numeri")
def add(a: int, b: int) -> int:
    return a + b

# 2) Esplicito: schema scritto a mano (consigliato per input complessi)
my_tool = Tool(
    name="save_doc",
    description="Salva un documento nella KB",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "content"],
    },
    func=lambda title, content, tags=None: ...,
)
```

`Tool.to_anthropic()` produce il payload che viene passato a
`messages.create(tools=[...])`.

### 3. `Orchestrator` = agente director + tool di delega

`core.orchestrator.Orchestrator` è esso stesso un `Agent` con due tool extra
generati automaticamente:

- `list_agents()` — elenca i subagent registrati nel `group`
- `delegate_to_agent(agent_name, task)` — esegue `AgentRegistry.get(name).run(task)`
  e restituisce l'output testuale al modello come `tool_result`

Il `system_prompt` dell'orchestrator viene costruito a runtime concatenando
le descrizioni di tutti i subagent presenti nel suo `group`, quindi appendendo
la `mission` specifica. Vedi
[src/ai_agents_creator/core/orchestrator.py](src/ai_agents_creator/core/orchestrator.py).

Risultato: l'orchestrator "vede" i subagent come capabilities e li chiama via
function-calling, esattamente come un agente normale chiama i propri tool.

### 4. `AgentRegistry`: discovery dinamica

`core.registry.AgentRegistry` è un registry in-memory con due dimensioni:

- registrazione per **nome** (lookup `O(1)` da parte di delegate / webhook /
  A2A server)
- registrazione per **gruppo** (l'orchestrator filtra solo i suoi subagent)

Ogni `Orchestrator` chiama `AgentRegistry.list(group)` al volo, quindi se
registri un nuovo agente *prima* di invocare l'orchestrator, viene scoperto
senza modifiche al codice esistente.

### 5. Provider switch: `providers/factory.py`

`build_client(settings)` ritorna l'istanza giusta dall'SDK ufficiale `anthropic`
in base a `LLM_PROVIDER`:

| Provider    | Classe SDK         | Variabili `.env`                                          |
|-------------|--------------------|-----------------------------------------------------------|
| `anthropic` | `Anthropic`        | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`                    |
| `bedrock`   | `AnthropicBedrock` | `AWS_*`, `BEDROCK_MODEL`                                  |
| `vertex`    | `AnthropicVertex`  | `VERTEX_PROJECT_ID`, `VERTEX_REGION`, `VERTEX_MODEL`      |

Tutte e tre espongono `messages.create(...)`, quindi `complete(...)` è un
wrapper unico che gli agenti usano senza saperne nulla.
`_validate_model_for_provider` fa fail-fast se l'id modello non è coerente col
provider (errore tipico: id Bedrock con `LLM_PROVIDER=anthropic`).

### 6. Tool MCP (Model Context Protocol)

`mcp/client.py` fornisce `load_mcp_tools([MCPServerConfig(...)])` che:

1. apre una sessione `stdio` verso il server MCP
2. chiama `list_tools()` e per ogni tool remoto crea un `core.tools.Tool` con
   nome `{server}__{tool}`
3. il `func` del Tool apre una nuova sessione stdio, esegue `call_tool(...)`,
   chiude e ritorna il testo

Così un MCP server "filesystem" o "github" diventa una lista di Tool che si
passano direttamente al costruttore di `Agent(tools=...)`.

### 7. Protocollo A2A (Agent-to-Agent)

Due moduli simmetrici:

- **`a2a/server.py`** — `APIRouter` FastAPI con endpoint:
  - `GET  /a2a/agents` — lista delle `AgentCard` (locali + orchestrator)
  - `GET  /a2a/agents/{name}` — card di un singolo agente
  - `POST /a2a/agents/{name}` — invoca un agente con un `A2AMessage`
    (`sender`, `task`, `context`, `reply_to?`) e ritorna `A2AResponse`
    (`output`, `artifacts`, `ok`, `error`)
  - `POST /a2a/orchestrators/{name}` — invoca un orchestrator
- **`a2a/client.py`** — `A2AClient(base_url)` con metodi `list_agents()`,
  `invoke_agent(name, task, context)`, `invoke_orchestrator(...)`.
  La funzione `a2a_tool(...)` produce un `Tool` che, quando invocato dall'LLM,
  fa un POST HTTP all'agente remoto e ritorna l'output come stringa.

Conseguenza pratica: un agente esterno è **indistinguibile** da un tool locale
dal punto di vista del modello. Lo stesso vale all'inverso: se monti
`build_a2a_router()` nella tua FastAPI app, qualsiasi sistema esterno può
chiamare i tuoi agenti.

Ogni agente può anche girare in **standalone** come microservizio indipendente
grazie a `agents/_helpers.py::standalone_app(agent)`, che produce una FastAPI
app con `/run`, `/health`, `/a2a/agents`, `/a2a/agents/{name}`. Vedi
[examples/AGENTS.md](examples/AGENTS.md) per le porte usate dai use case
built-in.

### 8. Trigger: CLI e Webhook

- **CLI** (`triggers/cli.py`, comando `aiagents`): `aiagents list`,
  `aiagents run <orchestrator> "<task>"`, `aiagents run-agent <name> "<task>"`.
- **Webhook FastAPI** (`triggers/webhook.py`): espone
  `POST /run/{orchestrator}` e `POST /run/agent/{agent}` protetti dall'header
  `X-Webhook-Secret`. La stessa app monta anche il router A2A, quindi un
  singolo processo serve sia webhook interni sia chiamate A2A esterne.

Entrambi chiamano `bootstrap_all()` (`agents/__init__.py`) che registra gli
orchestrator built-in nel registry; aggiungere un nuovo use case = aggiungere
un import lì dentro.

### 9. Esecuzione locale vs distribuita (stesso codice)

I gruppi di agenti built-in implementano un pattern utile da copiare:

```python
# src/ai_agents_creator/agents/knowledge_base/__init__.py (semplificato)
_AGENT_URL_VARS = {
    "kb_reader": "KB_READER_URL",
    "kb_classifier": "KB_CLASSIFIER_URL",
    ...
}

def register_kb_agents():
    for agent in _get_local_agents():
        # registra solo quelli SENZA URL remoto configurato
        if not os.environ.get(_AGENT_URL_VARS[agent.name], "").strip():
            AgentRegistry.register(agent, group=GROUP)

def _remote_agent_tools() -> list[Tool]:
    # per ogni URL configurato genera un a2a_tool
    return [a2a_tool(...) for agent_name, env_var in _AGENT_URL_VARS.items()
            if os.environ.get(env_var)]
```

Se imposti `KB_READER_URL=http://reader:8001`, quello specifico agente non
viene registrato in-process: l'orchestrator riceve invece un `delegate_to_kb_reader`
A2A tool. Mix and match per fare deploy ibridi (alcuni agenti locali, altri
distribuiti) senza toccare il codice del singolo agente.

---

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env        # poi modifica .env
```

## Configurazione `.env`

Tre modalità selezionabili con `LLM_PROVIDER`:

```
# --- Scelta provider ---
LLM_PROVIDER=anthropic         # oppure: bedrock | vertex

# --- Anthropic API ---
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6

# --- AWS Bedrock ---
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
BEDROCK_MODEL=anthropic.claude-sonnet-4-6

# --- Vertex AI ---
VERTEX_PROJECT_ID=my-gcp-project
VERTEX_REGION=global
VERTEX_MODEL=claude-sonnet-4-5

# --- A2A / Webhook ---
A2A_BASE_URL=http://localhost:8000
WEBHOOK_SECRET=cambia-questo

# --- Paths ---
KB_INPUT_DIR=./data/input
KB_OUTPUT_DIR=./data/knowledge_base
```

---

## Quick start

### Use case 1 — Knowledge Base builder

```bash
python examples/run_kb_builder.py
```

Pipeline: `kb_reader → kb_classifier → kb_writer → kb_indexer`. Dettagli in
[examples/AGENTS.md](examples/AGENTS.md#gruppo-knowledge_base).

### Use case 2 — Editorial Calendar

```bash
python examples/run_editorial_calendar.py --topic "AI agents" --days 14
```

Pipeline: `kb_researcher → strategist → planner → copywriter`. Dettagli in
[examples/AGENTS.md](examples/AGENTS.md#gruppo-editorial_calendar).

### Webhook + A2A server

```bash
uvicorn ai_agents_creator.triggers.webhook:app --reload
```

```bash
curl -X POST http://localhost:8000/run/knowledge_base \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: cambia-questo" \
  -d '{"task": "Aggiorna la KB dai file in ./data/input"}'
```

Stesso server espone `/a2a/...` per chiamate da agenti esterni. Vedi
[examples/a2a_external_client.py](examples/a2a_external_client.py) per i
client demo.

### CLI

```bash
aiagents list
aiagents run knowledge_base "Aggiorna la KB"
aiagents run-agent kb_indexer "Rigenera INDEX.md"
```

---

## Prossimi passi

- **Catalogo agenti integrati** + tabelle porte/env A2A → [examples/AGENTS.md](examples/AGENTS.md)
- **Guida per creare un nuovo agente** (con o senza A2A) → [CLAUDE.md](CLAUDE.md)
