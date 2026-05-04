# Lista Agenti

Ogni agente ha il proprio file dedicato in `src/ai_agents_creator/agents/`.  
Ogni cartella contiene:

- `__init__.py` — definizione dell'agente (`name`, `description`, `system_prompt`, `tools`).
- `server.py` — app FastAPI standalone per il deploy come microservizio indipendente.

---

## Gruppo: `knowledge_base`

Agenti del **KB Builder**: leggono contenuti da una cartella locale e aggiornano la knowledge base Markdown.

Orchestrator: `knowledge_base`

| Agente | File | Porta standalone | Variabile A2A remota | Descrizione |
|---|---|---|---|---|
| `kb_reader` | `agents/knowledge_base/kb_reader/` | `8001` | `KB_READER_URL` | Legge i file di input e produce testo pulito in JSON |
| `kb_classifier` | `agents/knowledge_base/kb_classifier/` | `8002` | `KB_CLASSIFIER_URL` | Assegna `category`, `tags`, `title`, `summary` al contenuto |
| `kb_writer` | `agents/knowledge_base/kb_writer/` | `8003` | `KB_WRITER_URL` | Scrive il documento `.md` definitivo con frontmatter nella KB |
| `kb_indexer` | `agents/knowledge_base/kb_indexer/` | `8004` | `KB_INDEXER_URL` | Rigenera `INDEX.md` e `index.json` della knowledge base |

### Pipeline KB Builder

```
input files
    └─► kb_reader   (testo pulito)
            └─► kb_classifier   (category / tags / title / summary)
                    └─► kb_writer   (scrive .md in KB_OUTPUT_DIR/categories/<cat>/)
                                └─► kb_indexer   (rigenera INDEX.md + index.json)
```

### Tool disponibili (`agents/knowledge_base/tools.py`)

| Tool | Descrizione |
|---|---|
| `list_input_files` | Elenca i file in `KB_INPUT_DIR` |
| `read_input_file` | Legge un file testuale da `KB_INPUT_DIR` |
| `write_kb_document` | Scrive un `.md` con frontmatter in `KB_OUTPUT_DIR/categories/<categoria>/` |
| `rebuild_index` | Scansiona `KB_OUTPUT_DIR/categories/**` e rigenera `INDEX.md` + `index.json` |

---

## Gruppo: `editorial_calendar`

Agenti del **Editorial Calendar**: accedono alla knowledge base e producono un calendario editoriale per i social.

Orchestrator: `editorial_calendar`

| Agente | File | Porta standalone | Variabile A2A remota | Descrizione |
|---|---|---|---|---|
| `kb_researcher` | `agents/editorial_calendar/kb_researcher/` | `8011` | `KB_RESEARCHER_URL` | Legge `INDEX.md` e carica **solo** i `.md` rilevanti per il topic |
| `strategist` | `agents/editorial_calendar/strategist/` | `8012` | `STRATEGIST_URL` | Definisce `audience`, `pillars`, `tone_of_voice`, `objectives` |
| `planner` | `agents/editorial_calendar/planner/` | `8013` | `PLANNER_URL` | Crea la lista strutturata di post (data / canale / formato / pillar) |
| `copywriter` | `agents/editorial_calendar/copywriter/` | `8014` | `COPYWRITER_URL` | Scrive `hook`, `body`, `cta`, `hashtags` e salva il calendario |

### Pipeline Editorial Calendar

```
topic + giorni + canali
    └─► kb_researcher   (selected_paths + key_insights dalla KB)
            └─► strategist   (audience / pillars / tone / objectives)
                    └─► planner   (items: date / channel / format / pillar)
                                └─► copywriter   (hook / body / cta / hashtags → salva calendar_*.md + .json)
```

### Tool disponibili (`agents/editorial_calendar/tools.py`)

| Tool | Descrizione |
|---|---|
| `load_kb_index` | Restituisce l'indice completo della KB (solo metadata, no contenuto) |
| `search_kb_index` | Cerca nell'indice i documenti per parole chiave / categorie |
| `load_kb_document` | Carica il testo completo di un singolo `.md` della KB |
| `save_editorial_calendar` | Salva `calendar_<timestamp>.md` + `.json` in `EDITORIAL_OUTPUT_DIR` |

---

## Deploy standalone di un singolo agente

Ogni agente può girare come microservizio indipendente (utile per deployment distribuito o scaling).

```bash
# Esempio: kb_reader su porta 8001
uvicorn ai_agents_creator.agents.knowledge_base.kb_reader.server:app --port 8001

# Esempio: copywriter su porta 8014
uvicorn ai_agents_creator.agents.editorial_calendar.copywriter.server:app --port 8014
```

Endpoint esposti da ogni standalone server:

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/health` | `GET` | Info agente (nome, descrizione, tool) |
| `/run` | `POST` | Esegui agente con `{"task": "..."}` |
| `/a2a/agents` | `GET` | `AgentCard` in formato A2A |
| `/a2a/agents/{name}` | `POST` | Invocazione A2A standard |

### Modalità distribuita via variabili d'ambiente

Se imposti `KB_READER_URL=http://host:8001` (o qualsiasi altra variabile della colonna
"Variabile A2A remota"), l'orchestrator **chiamerà quell'agente via HTTP A2A** invece
di eseguirlo in-process. Gli agenti senza URL configurato continuano a girare in locale.

```env
# .env — esempio deployment ibrido
KB_READER_URL=http://reader-service:8001
KB_WRITER_URL=http://writer-service:8003
# kb_classifier e kb_indexer restano in-process
```

---

## Aggiungere un nuovo agente

1. Crea la cartella e i file:

```
src/ai_agents_creator/agents/<gruppo>/<nome_agente>/
    __init__.py   ← definizione Agent
    server.py     ← standalone FastAPI app
```

2. **`__init__.py`** minimo:

```python
from ....core.agent import Agent
from ..tools import my_tool  # tool del gruppo

SYSTEM_PROMPT = "Sei l'agente XYZ..."

agent = Agent(
    name="my_agent",
    description="Cosa fa questo agente",
    system_prompt=SYSTEM_PROMPT,
    tools=[my_tool],
)
```

3. **`server.py`** minimo (scegli una porta libera):

```python
from ..._helpers import standalone_app
from . import agent

app = standalone_app(agent)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
```

4. Aggiungi `"my_agent": "MY_AGENT_URL"` nella dict `_AGENT_URL_VARS` di
   `agents/<gruppo>/__init__.py` e importa il tuo agent nella lista
   `_get_local_agents()`.

L'orchestrator del gruppo lo scoprirà automaticamente alla prossima esecuzione.
