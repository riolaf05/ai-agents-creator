# AI Agents Creator

Framework leggero in Python per costruire **agenti AI specializzati** basati sul
SDK di Claude (Anthropic), ispirato al modello dei *subagent* di Claude Code.

Caratteristiche principali:

- **Provider switch via `.env`**: stesso codice, usa **API Anthropic** oppure
  **AWS Bedrock** cambiando una variabile d'ambiente.
- **Agenti + Orchestrator**: definisci agenti specializzati (prompt, tool,
  modello) e lascia che un orchestrator li coordini per eseguire un task.
- **Tool MCP**: gli agenti possono usare tool esposti da server MCP (Model
  Context Protocol) locali o remoti.
- **Protocollo A2A** (Agent-to-Agent): i tuoi agenti possono essere **chiamati
  da** agenti esterni e **chiamare** agenti esterni via HTTP JSON.
- **Trigger**: esegui gli agenti via **CLI**, **webhook HTTP** (FastAPI) o
  scheduler.
- **Due use case pronti**:
  1. *Knowledge Base builder*: legge contenuti da una cartella locale e li
     trasforma in knowledge base `.md` categorizzata con `INDEX.md`.
  2. *Editorial Calendar*: legge la stessa KB (solo i `.md` rilevanti tramite
     l'indice) e produce un calendario editoriale per i social.

## Struttura

```
src/ai_agents_creator/
├── config.py                # Caricamento .env + selezione provider
├── providers/               # Anthropic API / AWS Bedrock
├── core/                    # Agent, Tool, Orchestrator, Registry
├── mcp/                     # Client MCP per tool esterni
├── a2a/                     # Server + client A2A
├── triggers/                # Webhook FastAPI, CLI
└── use_cases/
    ├── knowledge_base/
    └── editorial_calendar/
examples/                    # Script di esempio eseguibili
data/                        # Input e KB generata
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env        # poi modifica .env
```

## Configurazione `.env`

Esistono due modalità, selezionabili con `LLM_PROVIDER`:

```
# --- Scelta provider ---
LLM_PROVIDER=anthropic         # oppure: bedrock

# --- Anthropic API ---
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6

# --- AWS Bedrock ---
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
BEDROCK_MODEL=anthropic.claude-sonnet-4-6

# --- A2A / Webhook ---
A2A_BASE_URL=http://localhost:8000
WEBHOOK_SECRET=cambia-questo

# --- Paths ---
KB_INPUT_DIR=./data/input
KB_OUTPUT_DIR=./data/knowledge_base
```

## Use case 1 - Knowledge Base builder

```bash
python examples/run_kb_builder.py
```

Cosa succede:

1. Il `KBOrchestrator` ispeziona `data/input/`.
2. L'agente **Reader** estrae il testo dei file.
3. L'agente **Classifier** assegna categoria/tag.
4. L'agente **Writer** produce un `.md` pulito per ogni contenuto in
   `data/knowledge_base/categories/<categoria>/`.
5. L'agente **Indexer** (ri)genera `data/knowledge_base/INDEX.md` con la mappa
   degli argomenti.

## Use case 2 - Editorial Calendar

```bash
python examples/run_editorial_calendar.py --topic "AI agents" --days 14
```

Cosa succede:

1. L'agente **KBResearcher** legge `INDEX.md` e carica **solo** i `.md` delle
   categorie rilevanti al topic.
2. L'agente **Strategist** definisce pillar e obiettivi.
3. L'agente **Planner** genera il calendario (data, canale, tipo di post).
4. L'agente **Copywriter** scrive testi e hashtag.
5. L'output è un `editorial_calendar.md` + `editorial_calendar.json`.

## Trigger webhook

```bash
uvicorn ai_agents_creator.triggers.webhook:app --reload
```

Poi invoca:

```bash
curl -X POST http://localhost:8000/run/knowledge_base \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: cambia-questo" \
  -d '{"input_dir": "./data/input"}'
```

## A2A - comunicazione tra agenti

- Ogni orchestrator è esposto su `/a2a/<nome>` come endpoint JSON.
- Puoi chiamare un orchestrator da codice esterno con `A2AClient`.
- Un agente può a sua volta chiamare un agente esterno dichiarando un tool di
  tipo `A2ATool` (vedi `examples/a2a_external_client.py`).

## Aggiungere un nuovo agente

```python
from ai_agents_creator.core import Agent, AgentRegistry

my_agent = Agent(
    name="summarizer",
    description="Sintetizza testi lunghi in 5 bullet",
    system_prompt="Sei un esperto di sintesi...",
    tools=[],
)
AgentRegistry.register(my_agent)
```

L'orchestrator scoprirà automaticamente il nuovo agente.
