# filename: vectorize_kb_pipeline.py
#
# Reads Everstorm knowledge-base chunks from GCS, embeds each one with Vertex AI,
# and writes the text plus its vector into Cloud SQL (pgvector).
#
# NOTE ON CHUNKING: this pipeline embeds each INPUT FILE as a single vector. It
# has no chunking stage. That is why the files in data/kb/ are already
# section-level chunks rather than whole policy documents -- a 1,200-word document
# averaged into one 768-dimension vector retrieves badly, because it ends up
# meaning "shipping, generally" rather than any specific fact.
#
# In a production build the split belongs HERE, as a Beam stage between reading
# and embedding, so that a new document dropped in the bucket is chunked
# automatically. Pre-splitting is a workshop convenience.

import argparse
import logging
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io import fileio
from apache_beam.options.pipeline_options import GoogleCloudOptions
from google.cloud.sql.connector import Connector
from google import genai
from google.genai.types import EmbedContentConfig
import pg8000


class EmbedTextBatch(beam.DoFn):
    """Takes a batch of texts and generates embeddings using Vertex AI."""

    def __init__(self, project_id, region):
        self.project_id = project_id
        self.region = region

    def setup(self):
        self.client = genai.Client()

    def process(self, batch: list[tuple[str, str]]):
        if not batch:
            return
        filenames = [item[0] for item in batch]
        contents = [item[1] for item in batch]
        try:
            #REPLACE-EMBEDDING-LOGIC

            for filename, content, embedding_object in zip(filenames, contents, result.embeddings):
                if content.strip():
                    yield (content.strip(), embedding_object.values)
        except Exception as e:
            # A bad batch is tagged and logged, not fatal. The remaining batches
            # keep going -- this is the difference between a pipeline and a script.
            logging.error(f"Could not process batch for files {filenames}: {e}")
            for filename, content in zip(filenames, contents):
                yield beam.pvalue.TaggedOutput('failed', (filename, str(e)))


class WriteChunkToKnowledgeBase(beam.DoFn):
    """Writes a chunk's text and its vector embedding to Cloud SQL."""

    def __init__(self, project_id, region, instance_name, db_name, db_password, kb_table):
        self.project_id = project_id
        self.region = region
        self.instance_name = instance_name
        self.db_name = db_name
        self.db_password = db_password
        self.kb_table = kb_table

    def setup(self):
        self.connector = Connector()
        self.conn = self.connector.connect(
            f"{self.project_id}:{self.region}:{self.instance_name}", "pg8000",
            user="postgres",
            password=self.db_password,
            db=self.db_name
        )
        self.cursor = self.conn.cursor()

    def process(self, element: tuple[str, list[float]]):
        chunk_text, vector = element
        try:
            vector_string = str(vector)
            self.cursor.execute(
                f"INSERT INTO {self.kb_table} (chunk_content, embedding) VALUES (%s, %s)",
                (chunk_text, vector_string))
            self.conn.commit()
        except Exception as e:
            logging.error(f"Failed to write chunk to the knowledge base: {e}. Rolling back.")
            self.conn.rollback()

    def teardown(self):
        self.conn.close()
        self.connector.close()


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_pattern", required=True, help="GCS path for input files")
    parser.add_argument("--instance_name", required=True, help="Cloud SQL instance connection name")
    parser.add_argument("--db_name", default="everstorm_kb", help="PostgreSQL database name")
    parser.add_argument("--db_password", default="1234qwer", help="PostgreSQL password")
    parser.add_argument("--kb_table", default="policy_chunks", help="Target table name")

    known_args, pipeline_args = parser.parse_known_args(argv)
    pipeline_options = PipelineOptions(pipeline_args, save_main_session=True)

    project = pipeline_options.view_as(GoogleCloudOptions).project
    region = pipeline_options.view_as(GoogleCloudOptions).region

    with beam.Pipeline(options=pipeline_options) as pipeline:
        #REPLACE ME-READFILE

        #REPLACE ME-EMBEDDING

        #REPLACE ME-WRITE TO DB

        #REPLACE ME-LOG FAILURES


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()
