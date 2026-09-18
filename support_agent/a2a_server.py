from a2a.server.apps import A2AStarletteApplication
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
import os
import logging
from dotenv import load_dotenv
from support_agent.agent_executor import SupportAgentExecutor
import uvicorn
from support_agent import agent


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

host = os.environ.get("A2A_HOST", "localhost")
port = int(os.environ.get("A2A_PORT", 10003))
PUBLIC_URL = os.environ.get("PUBLIC_URL")


class EverstormSupportAgent:
    """A customer-support agent answering from Everstorm's policy knowledge base."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self._agent = self._build_agent()
        self.runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="policy_lookup",
            name="Everstorm Policy Lookup",
            description="""
            Answers customer questions about Everstorm Outfitters' shipping, returns,
            warranty, payment and product policies. The agent embeds the question,
            runs a semantic search over the vectorised policy knowledge base, and
            answers only from the passages it retrieves -- quoting the specific
            figure, date or condition, naming the source document, and flagging when
            a retrieved passage comes from a superseded revision.
            """,
            tags=["customer-support", "retail", "policy", "rag"],
            examples=[
                "How long do I have to return something?",
                "What's the free shipping threshold?",
                "I'm in the UK, do I pay import duty?",
                "My Summit GTX boots have come apart at the sole. Am I covered?",
            ],
        )
        self.agent_card = AgentCard(
            name="Everstorm Support Agent",
            description="""
            A customer-support agent for Everstorm Outfitters, an outdoor gear
            retailer. It answers policy questions by retrieving from the company's
            own documents rather than from general knowledge, so every answer is
            traceable to a source and current as of the document revision in force.
            """,
            url=f"{PUBLIC_URL}",
            version="1.0.0",
            defaultInputModes=EverstormSupportAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=EverstormSupportAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

    def get_processing_message(self) -> str:
        return "Searching the Everstorm policy knowledge base..."

    def _build_agent(self) -> LlmAgent:
        """Returns the configured support agent."""
        return agent.root_agent


if __name__ == '__main__':
    try:
        support_agent = EverstormSupportAgent()

        request_handler = DefaultRequestHandler(
            agent_executor=SupportAgentExecutor(
                support_agent.runner, support_agent.agent_card
            ),
            task_store=InMemoryTaskStore(),
        )

        server = A2AStarletteApplication(
            agent_card=support_agent.agent_card,
            http_handler=request_handler,
        )
        logger.info(f"Starting server with Agent Card: {support_agent.agent_card.name}")

        uvicorn.run(server.build(), host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)
