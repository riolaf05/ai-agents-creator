"""Standalone server per kb_researcher.

    uvicorn ai_agents_creator.agents.editorial_calendar.kb_researcher.server:app --port 8011
"""

from ..._helpers import standalone_app
from . import agent

app = standalone_app(agent)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
