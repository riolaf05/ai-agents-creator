"""Standalone server per kb_indexer.

    uvicorn ai_agents_creator.agents.knowledge_base.kb_indexer.server:app --port 8004
"""

from ..._helpers import standalone_app
from . import agent

app = standalone_app(agent)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
