import logging
from google.adk.agents.llm_agent import LlmAgent

import os
import pg8000
from google import genai
from google.genai.types import EmbedContentConfig
from google.cloud.sql.connector import Connector
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
load_dotenv()
connector = Connector()
client = genai.Client()

# Table holding the vectorised policy chunks. Written by the Dataflow pipeline
# in pipeline/vectorize_kb_pipeline.py -- keep the two in step.
KB_TABLE = os.environ.get("KB_TABLE", "policy_chunks")


def get_db_connection():
    """Establishes a connection to the Cloud SQL database."""
    conn = connector.connect(
        f"{os.environ['PROJECT_ID']}:{os.environ['REGION']}:{os.environ['INSTANCE_NAME']}",
        "pg8000",
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        db=os.environ["DB_NAME"]
    )
    return conn


# --- The Support Agent's Tool ---
def policy_lookup(question: str) -> str:
    """
    Searches Everstorm's policy knowledge base for passages relevant to a
    customer question, and returns the closest matches.

    Args:
        question: The customer's question, in natural language.
    """
    print(f"Searching the Everstorm knowledge base for: {question}...")
    try:

        #REPLACE RAG-CONVERT EMBEDDING

        query_embedding_list = result.embeddings[0].values
        query_embedding = str(query_embedding_list)

        # 2. Search the knowledge base
        db_conn = get_db_connection()
        cursor = db_conn.cursor()

        #REPLACE RAG-RETRIEVE

        results = cursor.fetchall()
        cursor.close()
        db_conn.close()

        if not results:
            return (
                f"The knowledge base contains no passage relevant to '{question}'. "
                "Tell the customer you do not know and point them at the right team."
            )

        retrieved_knowledge = "\n---\n".join([row[0] for row in results])
        print(f"Retrieved {len(results)} passages.")
        return retrieved_knowledge

    except Exception as e:
        print(f"Error while searching the knowledge base: {e}")
        return (
            "The knowledge base could not be reached. Tell the customer you cannot "
            "confirm the policy right now rather than guessing at it."
        )


# Define the Everstorm Support Agent

#REPLACE-CALL RAG
