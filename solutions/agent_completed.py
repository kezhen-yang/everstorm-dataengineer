# Reference copy of support_agent/agent.py with all three #REPLACE markers filled.
# Keep this out of the student path -- it is here so the instructor can recover
# quickly if a live edit goes wrong mid-session.

import logging
from google.adk.agents.llm_agent import LlmAgent

import os
import pg8000
from google import genai
from google.genai.types import EmbedContentConfig
from google.cloud.sql.connector import Connector
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()
connector = Connector()
client = genai.Client()

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


def policy_lookup(question: str) -> str:
    """
    Searches Everstorm's policy knowledge base for passages relevant to a
    customer question, and returns the closest matches.

    Args:
        question: The customer's question, in natural language.
    """
    print(f"Searching the Everstorm knowledge base for: {question}...")
    try:
        # --- was #REPLACE RAG-CONVERT EMBEDDING ---
        # RETRIEVAL_QUERY, not RETRIEVAL_DOCUMENT. Documents and questions are
        # embedded with deliberately different strategies so that a question
        # lands near its answer. The upstream codelab uses RETRIEVAL_DOCUMENT
        # here; both "work" because the vectors share a space, but this is the
        # correct asymmetric pairing and it matches the BigQuery VECTOR_SEARCH
        # example taught earlier in the workshop.
        result = client.models.embed_content(
            model="text-embedding-005",
            contents=question,
            config=EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768,
            ),
        )

        query_embedding_list = result.embeddings[0].values
        query_embedding = str(query_embedding_list)

        db_conn = get_db_connection()
        cursor = db_conn.cursor()

        # --- was #REPLACE RAG-RETRIEVE ---
        # <=> is the pgvector cosine-distance operator. It must match the
        # vector_cosine_ops used when the HNSW index was built, or Postgres
        # silently ignores the index and sequentially scans every row.
        cursor.execute(
            f"SELECT chunk_content FROM {KB_TABLE} ORDER BY embedding <=> %s LIMIT 5",
            ([query_embedding]),
        )

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


# --- was #REPLACE-CALL RAG ---
root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="everstorm_support_agent",
    instruction="""
        You are a senior customer-support advisor for Everstorm Outfitters, an
        outdoor gear retailer. You answer using the company's own policy
        documents, not from general knowledge about retail.

        **Your process:**
        1. ALWAYS call `policy_lookup` first, before answering anything.
        2. Answer ONLY from what it returns. Quote the specific figure, date or
           condition rather than paraphrasing it away.
        3. Every retrieved passage begins with a context line naming the
           document, its revision and its status. USE IT:
           - If a passage is marked `Status: superseded`, do NOT use it for a
             current question. Prefer the `Status: current` passage. Mention the
             older value only if the customer asked what the policy used to be.
           - If passages disagree, say so explicitly, name both documents, and
             state which one governs.
        4. Regional rules are not interchangeable. The EU and the UK are treated
           differently on duties. Never apply an EU rule to a UK order.
        5. If the retrieved passages do not contain the answer, say you do not
           know and name the team to contact. NEVER invent a policy, a number,
           or a date.

        **Output format:** a direct answer first, then the specific conditions
        or exceptions, then the document you relied on.
    """,
    tools=[policy_lookup],
)
