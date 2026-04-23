# Model Context Protocol (MCP)

Il Model Context Protocol è un protocollo aperto che standardizza il modo in
cui gli LLM accedono a **tool** e **risorse** esterne. Un server MCP espone:

- **tools**: funzioni invocabili dal modello.
- **resources**: dati leggibili (file, DB, API).
- **prompts**: template di prompt riutilizzabili.

Un client MCP (tipicamente un'app agentica) si connette via stdio o HTTP,
chiama `list_tools`, e poi `call_tool`. Questo disaccoppia l'agente dalle
integrazioni e permette di riusare lo stesso tool in app diverse (Claude
Desktop, Cursor, n8n, IDE, pipeline CI).

Casi d'uso tipici: filesystem locale, GitHub, Slack, database, CRM.
