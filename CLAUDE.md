# CLAUDE.md — Guida per creare nuovi agenti

Questa guida spiega come usare questo repo come **template** per costruire
nuovi agenti AI. Copre due percorsi:

- **Percorso A — Agente in-process (senza A2A)**: vivono solo dentro Python,
  registrati nel `AgentRegistry`. Più semplice, ottimo per iniziare.
- **Percorso B — Agente con supporto A2A**: lo stesso agente è anche esposto
  via HTTP, può essere chiamato da sistemi esterni e/o deployato come
  microservizio indipendente.

Se non sai quale scegliere: parti dal **Percorso A**. Aggiungere A2A dopo è un
delta piccolo (vedi sezione "Da in-process ad A2A in 3 mosse").

> Per i concetti (Agent / Tool / Orchestrator / Registry / A2A / MCP) leggi
> prima la sezione **Architettura tecnica degli agenti** del [README.md](README.md).
> Qui ci concentriamo sui comandi e i file da scrivere.

---

## Pre-flight

1. Ambiente:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows PowerShell
   pip install -r requirements.txt
   copy .env.example .env        # imposta LLM_PROVIDER + chiavi
   ```
2. Verifica che il provider risponda:
   ```bash
   aiagents list
   ```
3. Decidi:
   - un **nome agente** (snake_case, es. `summarizer`)
   - un **gruppo** (= use case / orchestrator) — riusa uno esistente
     (`knowledge_base`, `editorial_calendar`) oppure creane uno nuovo
   - se serve **A2A** (sì se: chiamate da sistemi esterni, deploy come
     microservizio, scaling indipendente; no altrimenti)

---

## Anatomia minima di un agente

Indipendentemente dal percorso, un agente è sempre questa cosa qui:

```python
from ai_agents_creator.core import Agent
from ai_agents_creator.core.tools import tool

@tool(description="Conta le parole di un testo")
def word_count(text: str) -> int:
    return len(text.split())

summarizer = Agent(
    name="summarizer",
    description="Sintetizza testi lunghi in 5 bullet",
    system_prompt=(
        "Sei un esperto di sintesi. Produci esattamente 5 bullet, "
        "ognuno < 20 parole. Usa il tool word_count se serve."
    ),
    tools=[word_count],
)
```

`Agent.run("testo lungo...")` esegue il mini-loop agentic descritto nel README.

---

## Percorso A — Agente in-process (no A2A)

Adatto a: pipeline interne, batch job, esperimenti, agenti chiamati solo da
altri agenti Python in **questo** processo.

### A.1 — Caso veloce: aggiungere un agente a un gruppo esistente

Esempio: aggiungere `summarizer` al gruppo `knowledge_base`.

1. Crea il modulo dell'agente:

   ```
   src/ai_agents_creator/agents/knowledge_base/summarizer/
       __init__.py
   ```

2. Contenuto di `__init__.py`:

   ```python
   from ....core.agent import Agent
   from ..tools import read_input_file  # riusa i tool del gruppo

   SYSTEM_PROMPT = "Sei l'agente Summarizer..."

   agent = Agent(
       name="summarizer",
       description="Riassume in 5 bullet i testi della KB",
       system_prompt=SYSTEM_PROMPT,
       tools=[read_input_file],
   )
   ```

3. Aggancialo al gruppo. Apri
   [src/ai_agents_creator/agents/knowledge_base/\_\_init\_\_.py](src/ai_agents_creator/agents/knowledge_base/__init__.py)
   e aggiungi l'import in `_get_local_agents()`:

   ```python
   def _get_local_agents() -> list[Agent]:
       from .kb_classifier import agent as classifier
       from .kb_indexer import agent as indexer
       from .kb_reader import agent as reader
       from .kb_writer import agent as writer
       from .summarizer import agent as summarizer  # <-- NEW
       return [reader, classifier, writer, indexer, summarizer]
   ```

4. (Opzionale ma consigliato) aggiorna la `mission` dell'orchestrator
   per istruirlo a usare il nuovo agente quando serve.

5. Verifica:
   ```bash
   aiagents list                       # deve apparire 'summarizer'
   aiagents run-agent summarizer "Riassumi questo testo: ..."
   ```

L'orchestrator del gruppo lo scopre automaticamente alla prossima esecuzione
(`AgentRegistry.list(group)` viene riletto a ogni `Orchestrator.run`).

### A.2 — Caso: nuovo gruppo (= nuovo use case / orchestrator)

Quando il tuo problema non è una variazione di un use case esistente.

1. Scaffold:

   ```
   src/ai_agents_creator/agents/<mio_gruppo>/
       __init__.py        # orchestrator + register_*_agents()
       tools.py           # tool condivisi tra agenti del gruppo
       <agente_1>/
           __init__.py    # definizione Agent
       <agente_2>/
           __init__.py
       ...
   ```

2. `tools.py`: definisci i tool del gruppo (`@tool` o `Tool(...)`).

3. Ogni `<agente_X>/__init__.py`: come nel caso A.1.

4. `<mio_gruppo>/__init__.py` minimo (senza A2A):

   ```python
   from __future__ import annotations

   from ...core.agent import Agent
   from ...core.orchestrator import Orchestrator
   from ...core.registry import AgentRegistry

   GROUP = "mio_gruppo"
   MISSION = "Cosa deve fare l'orchestrator, pipeline obbligatoria, regole..."

   def _get_local_agents() -> list[Agent]:
       from .agente_1 import agent as a1
       from .agente_2 import agent as a2
       return [a1, a2]

   def register_mio_gruppo_agents() -> None:
       for agent in _get_local_agents():
           AgentRegistry.register(agent, group=GROUP)

   def build_mio_gruppo_orchestrator() -> Orchestrator:
       register_mio_gruppo_agents()
       return Orchestrator(name=GROUP, group=GROUP, mission=MISSION)
   ```

5. Registra l'orchestrator nel bootstrap globale. Apri
   [src/ai_agents_creator/agents/\_\_init\_\_.py](src/ai_agents_creator/agents/__init__.py)
   e aggiungi:

   ```python
   def bootstrap_all() -> None:
       global _BOOTSTRAPPED
       if _BOOTSTRAPPED:
           return
       from .knowledge_base import build_kb_orchestrator
       from .editorial_calendar import build_editorial_orchestrator
       from .mio_gruppo import build_mio_gruppo_orchestrator  # <-- NEW

       register_orchestrator(build_kb_orchestrator())
       register_orchestrator(build_editorial_orchestrator())
       register_orchestrator(build_mio_gruppo_orchestrator())  # <-- NEW
       _BOOTSTRAPPED = True
   ```

6. (Opzionale) script di esempio in `examples/run_mio_gruppo.py` che chiama
   `build_mio_gruppo_orchestrator().run("...")` — vedi
   [examples/run_kb_builder.py](examples/run_kb_builder.py) come modello.

7. Verifica:
   ```bash
   aiagents list                              # nuovo orchestrator visibile
   aiagents run mio_gruppo "obiettivo..."
   ```

---

## Percorso B — Agente con supporto A2A

Adatto a: chiamate da sistemi esterni, deploy come microservizio, scaling per
agente, mix di agenti locali e remoti dietro lo stesso orchestrator.

> A2A in questo repo è **opt-in per singolo agente**. Puoi avere un gruppo
> dove `agente_1` è locale e `agente_2` è remoto via A2A, scegliendo da `.env`.

### B.1 — Esporre un agente esistente via A2A (automatico)

Se il tuo agente è già registrato nel `AgentRegistry` (Percorso A), è **già
raggiungibile via A2A** appena avvii il webhook server:

```bash
uvicorn ai_agents_creator.triggers.webhook:app --reload
```

Endpoint disponibili (forniti da `a2a/server.py`):

| Endpoint                          | Metodo | Cosa fa                                  |
|-----------------------------------|--------|------------------------------------------|
| `/a2a/agents`                     | GET    | Elenco `AgentCard` di tutti gli agenti   |
| `/a2a/agents/{name}`              | GET    | Card di un singolo agente                |
| `/a2a/agents/{name}`              | POST   | Invoca l'agente con un `A2AMessage`      |
| `/a2a/orchestrators/{name}`       | POST   | Invoca un orchestrator                   |

Test rapido:

```bash
curl http://localhost:8000/a2a/agents

curl -X POST http://localhost:8000/a2a/agents/summarizer \
  -H "Content-Type: application/json" \
  -d '{"sender": "tester", "task": "Riassumi questo testo: ..."}'
```

### B.2 — Standalone microservice per un singolo agente

Quando vuoi deployare l'agente in un container/host dedicato.

1. Crea `server.py` accanto al tuo `__init__.py`:

   ```python
   # src/ai_agents_creator/agents/<gruppo>/<nome_agente>/server.py
   from ..._helpers import standalone_app
   from . import agent

   app = standalone_app(agent)

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8005)   # scegli porta libera
   ```

2. Avvia:
   ```bash
   uvicorn ai_agents_creator.agents.<gruppo>.<nome_agente>.server:app --port 8005
   ```

3. Il microservizio espone `/health`, `/run`, `/a2a/agents`, `/a2a/agents/{name}`.

> Lista delle porte standard usate dagli agenti built-in:
> [examples/AGENTS.md § Deploy standalone](examples/AGENTS.md#deploy-standalone-di-un-singolo-agente).

### B.3 — Deploy ibrido: alcuni agenti locali, altri remoti

Questo è il pattern interessante: l'orchestrator gira sempre in-process, ma
delega via HTTP A2A a quegli agenti che hai messo su altri host.

1. Nel `__init__.py` del gruppo, dichiara la mappa nome -> env var:

   ```python
   _AGENT_URL_VARS = {
       "agente_1": "AGENTE_1_URL",
       "agente_2": "AGENTE_2_URL",
   }
   ```

2. Implementa **registrazione condizionale** e **tool A2A remoti**:

   ```python
   import os
   from ...a2a.client import a2a_tool
   from ...core.tools import Tool

   def register_mio_gruppo_agents() -> None:
       for agent in _get_local_agents():
           # registra in-process SOLO se non c'e' un URL remoto
           if not os.environ.get(_AGENT_URL_VARS.get(agent.name, ""), "").strip():
               AgentRegistry.register(agent, group=GROUP)

   def _remote_agent_tools() -> list[Tool]:
       tools: list[Tool] = []
       for agent_name, env_var in _AGENT_URL_VARS.items():
           url = os.environ.get(env_var, "").strip()
           if url:
               tools.append(a2a_tool(
                   tool_name=f"delegate_to_{agent_name}",
                   description=f"Chiama l'agente remoto {agent_name} via A2A",
                   base_url=url,
                   remote_agent=agent_name,
               ))
       return tools

   def build_mio_gruppo_orchestrator() -> Orchestrator:
       register_mio_gruppo_agents()
       return Orchestrator(
           name=GROUP, group=GROUP, mission=MISSION,
           extra_tools=_remote_agent_tools(),
       )
   ```

3. Configura le URL in `.env` solo per gli agenti che vuoi remoti:

   ```env
   AGENTE_1_URL=http://agente1-service:8005    # remoto
   # AGENTE_2_URL non settato                 # resta in-process
   ```

4. L'orchestrator vede `agente_2` come subagent locale (tool `delegate_to_agent`)
   e `agente_1` come tool A2A separato (`delegate_to_agente_1`). Il modello
   capisce la differenza dai nomi/descrizioni.

> Modello vivente di questo pattern:
> [agents/knowledge_base/\_\_init\_\_.py](src/ai_agents_creator/agents/knowledge_base/__init__.py).

### B.4 — Chiamare un agente esterno (di un altro team / partner)

Se il partner espone un endpoint compatibile A2A:

```python
from ai_agents_creator.a2a.client import a2a_tool
from ai_agents_creator.core import Agent

translator = a2a_tool(
    tool_name="external_translator",
    description="Traduce IT->EN usando l'agente del partner",
    base_url="https://partner.example.com",
    remote_agent="translator",
)

my_agent = Agent(
    name="multilingual_writer",
    description="Scrive post bilingue",
    system_prompt="...",
    tools=[translator],
)
```

Per il modello `external_translator` è un tool come gli altri. Lo schema input
del tool è fisso (`task: str`, `context: object?`). Esempio completo in
[examples/a2a_external_client.py](examples/a2a_external_client.py).

---

## Da in-process ad A2A in 3 mosse

Hai un agente del Percorso A e vuoi aprirlo all'esterno o spostarlo su un altro
host? Tutto sommato è poco.

1. **Aggiungi `server.py`** nella cartella dell'agente (vedi B.2). Questo lo
   rende deployabile standalone. Non rompe niente all'in-process.
2. **Aggiungi `_AGENT_URL_VARS` + `_remote_agent_tools()`** nel `__init__.py`
   del gruppo (vedi B.3). Senza env vars il comportamento resta identico.
3. **Setta la env var** `<NOME>_URL` solo quando vuoi switchare:
   - assente -> in-process come prima
   - presente -> l'orchestrator chiama il microservizio via A2A

---

## Aggiungere tool agli agenti

Tre opzioni, dalla più semplice alla più potente.

### 1. `@tool` decorator (signature -> schema)

Bene per tool con tipi semplici e schema "scopribile":

```python
from ai_agents_creator.core.tools import tool

@tool(description="Esegue una query SQL read-only")
def run_query(query: str, limit: int = 100) -> str:
    return db.fetch(query, limit=limit)
```

### 2. `Tool(...)` esplicito (schema JSON scritto a mano)

Obbligatorio per oggetti annidati / array tipizzati / enum:

```python
from ai_agents_creator.core.tools import Tool

save_doc = Tool(
    name="save_doc",
    description="Salva un documento .md con frontmatter",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "category": {"type": "string", "enum": ["news", "guide", "ref"]},
            "tags": {"type": "array", "items": {"type": "string"}},
            "content": {"type": "string"},
        },
        "required": ["title", "category", "content"],
    },
    func=_save_doc_impl,
)
```

### 3. Tool da MCP server

Per integrare server MCP esterni (filesystem, github, postgres, custom...):

```python
from ai_agents_creator.mcp import MCPServerConfig, load_mcp_tools

servers = [
    MCPServerConfig(
        name="fs",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./data"],
    ),
]
mcp_tools = load_mcp_tools(servers)   # lista di Tool, nome: "fs__<tool_name>"

my_agent = Agent(name="reader", ..., tools=[*mcp_tools])
```

Vedi [src/ai_agents_creator/mcp/client.py](src/ai_agents_creator/mcp/client.py).

---

## Checklist finale

Prima di considerare un agente "pronto":

- [ ] `name` è snake_case unico nel registry
- [ ] `description` è una frase: l'orchestrator la mette nel suo prompt
- [ ] `system_prompt`: include regole, formato output atteso, lista dei tool
      raccomandati per nome
- [ ] Ogni tool ha `description` chiara: l'LLM sceglie i tool leggendola
- [ ] Tool con input complesso hanno `input_schema` esplicito (non inferito)
- [ ] L'agente compare in `aiagents list`
- [ ] (Se è in un gruppo) l'orchestrator del gruppo lo cita nella `mission`
- [ ] (Solo A2A) `server.py` presente, porta non in conflitto, `/health` risponde
- [ ] (Solo A2A) variabile `<NOME>_URL` documentata in `.env.example` se è un
      agente che può girare remoto

---

## Riferimenti rapidi

| Cosa                                          | File                                                                              |
|-----------------------------------------------|-----------------------------------------------------------------------------------|
| Loop agentic e parsing tool-use               | [src/ai_agents_creator/core/agent.py](src/ai_agents_creator/core/agent.py)        |
| Definizione `Tool` + decorator `@tool`        | [src/ai_agents_creator/core/tools.py](src/ai_agents_creator/core/tools.py)        |
| Orchestrator con `delegate_to_agent`          | [src/ai_agents_creator/core/orchestrator.py](src/ai_agents_creator/core/orchestrator.py) |
| Registry globale                              | [src/ai_agents_creator/core/registry.py](src/ai_agents_creator/core/registry.py)  |
| Provider switch (Anthropic/Bedrock/Vertex)    | [src/ai_agents_creator/providers/factory.py](src/ai_agents_creator/providers/factory.py) |
| Server A2A (FastAPI router)                   | [src/ai_agents_creator/a2a/server.py](src/ai_agents_creator/a2a/server.py)        |
| Client A2A + `a2a_tool` factory               | [src/ai_agents_creator/a2a/client.py](src/ai_agents_creator/a2a/client.py)        |
| `standalone_app(agent)` per microservice      | [src/ai_agents_creator/agents/_helpers.py](src/ai_agents_creator/agents/_helpers.py) |
| Client MCP (stdio)                            | [src/ai_agents_creator/mcp/client.py](src/ai_agents_creator/mcp/client.py)        |
| Webhook FastAPI                               | [src/ai_agents_creator/triggers/webhook.py](src/ai_agents_creator/triggers/webhook.py) |
| CLI `aiagents`                                | [src/ai_agents_creator/triggers/cli.py](src/ai_agents_creator/triggers/cli.py)    |
| Catalogo agenti built-in (porte/env A2A)      | [examples/AGENTS.md](examples/AGENTS.md)                                          |
| Esempi A2A end-to-end                         | [examples/a2a_external_client.py](examples/a2a_external_client.py)                |
