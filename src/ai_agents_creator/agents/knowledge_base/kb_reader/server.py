"""Standalone server per kb_reader.

    uvicorn ai_agents_creator.agents.knowledge_base.kb_reader.server:app --port 8001
"""

from ..._helpers import standalone_app
from . import agent

app = standalone_app(agent)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
