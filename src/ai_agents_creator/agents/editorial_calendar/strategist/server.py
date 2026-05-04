"""Standalone server per strategist.

    uvicorn ai_agents_creator.agents.editorial_calendar.strategist.server:app --port 8012
"""

from ..._helpers import standalone_app
from . import agent

app = standalone_app(agent)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
