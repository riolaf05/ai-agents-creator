# Quickstart

## Come iniziare

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy .env.example .env
```

Poi modifica `.env`: imposta `ANTHROPIC_API_KEY` (con `LLM_PROVIDER=anthropic`) **oppure** credenziali AWS e `BEDROCK_MODEL` (con `LLM_PROVIDER=bedrock`).

Esegui gli esempi dalla root del progetto:

```bash
python examples/run_kb_builder.py
python examples/run_editorial_calendar.py --topic "AI agents" --days 14 --channels linkedin,x
```

Avvia il server webhook + A2A (in un terminale separato):

```bash
uvicorn ai_agents_creator.triggers.webhook:app --reload
```

Con il server in ascolto, prova il client A2A di esempio:

```bash
python examples/a2a_external_client.py
```

Opzionale: dalla root puoi usare la CLI dopo `pip install -e .`:

```bash
aiagents list
aiagents run knowledge_base "Aggiorna la KB dai file in ./data/input"
```
