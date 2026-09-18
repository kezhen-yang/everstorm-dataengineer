# Setup and command reference

Every command, in order. For the narrated 2-hour teaching version with speaker
notes and timings, see `TEACHING-FLOW.md` in the companion notes repo.

---

## 0. Environment

```bash
gcloud auth list

git clone https://github.com/kezhen-yang/everstorm-dataengineer.git ~/everstorm-dataengineer
cd ~/everstorm-dataengineer
chmod +x *.sh
./init.sh
gcloud config set project $(cat ~/project_id.txt) --quiet
```

### Enable APIs

```bash
gcloud services enable \
  storage.googleapis.com bigquery.googleapis.com sqladmin.googleapis.com \
  aiplatform.googleapis.com dataflow.googleapis.com pubsub.googleapis.com \
  cloudfunctions.googleapis.com run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com iam.googleapis.com compute.googleapis.com \
  cloudresourcemanager.googleapis.com cloudaicompanion.googleapis.com \
  bigqueryunified.googleapis.com
```

### Artifact Registry

```bash
source ./set_env.sh
gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker --location=$REGION \
  --description="Everstorm workshop images"
```

### IAM

```bash
source ./set_env.sh
for ROLE in storage.admin bigquery.admin dataflow.admin cloudsql.admin \
            pubsub.admin aiplatform.user cloudbuild.builds.editor \
            artifactregistry.admin run.admin iam.serviceAccountUser \
            logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME" --role="roles/$ROLE" --quiet
done
```

### Provision and upload

```bash
source ./set_env.sh
./data_setup.sh          # Cloud SQL (~15 min, background) + bucket + data upload
```

### Verify

```bash
gcloud storage ls gs://${BUCKET_NAME}/tickets/ | wc -l                  # 180
gcloud storage ls gs://${BUCKET_NAME}/kb/      | wc -l                  # 263
gcloud sql instances describe $INSTANCE_NAME --format='value(state)'    # RUNNABLE
```

---

## Part 1 — BigQuery knowledge base

### Connection, dataset, permissions

```bash
source ./set_env.sh

bq mk --connection --connection_type=CLOUD_RESOURCE \
  --project_id=${PROJECT_ID} --location=${REGION} gcs-connection

bq --location=${REGION} mk --dataset ${PROJECT_ID}:${BQ_DATASET}

export CONNECTION_SA=$(bq show --connection --project_id=${PROJECT_ID} \
  --location=${REGION} --format=json gcs-connection | jq -r '.cloudResource.serviceAccountId')
echo "Connection SA: $CONNECTION_SA"

gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:$CONNECTION_SA" --role="roles/storage.objectViewer"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:$CONNECTION_SA" --role="roles/aiplatform.user"

echo "${PROJECT_ID}.${REGION}.gcs-connection"   # paste into the SQL below
echo $BUCKET_NAME
```

### External table

```sql
CREATE OR REPLACE EXTERNAL TABLE everstorm_data.raw_tickets_table (
  raw_text STRING
)
OPTIONS (
  format = 'CSV',
  field_delimiter = '§',
  quote = '',
  uris = ['gs://REPLACE-WITH-YOUR-BUCKET/tickets/*']
);

SELECT COUNT(*) FROM everstorm_data.raw_tickets_table;   -- expect 180
```

`field_delimiter` is a character that never appears in the source text, so the
whole line lands in one column. `quote = ''` stops ordinary prose punctuation
from opening CSV fields. **This reads one row per line** — hence the pre-flattened
ticket files.

### Model reference

```sql
CREATE OR REPLACE MODEL everstorm_data.gemini_flash_model
REMOTE WITH CONNECTION `REPLACE-WITH-YOUR-FULL-CONNECTION-STRING`
OPTIONS (endpoint = 'gemini-2.5-flash');
```

### Extraction

```sql
CREATE OR REPLACE TABLE everstorm_data.structured_tickets AS
SELECT ml_generate_text_result AS structured_data
FROM ML.GENERATE_TEXT(
  MODEL everstorm_data.gemini_flash_model,
  (
    SELECT CONCAT(
      """
      From the following customer-support case note, extract structured data
      into a single, valid JSON object.

      Your output must strictly conform to this structure and these data types.
      Do not add, remove, or rename any keys.

      {
        "ticket": {
          "ticket_id": "string",
          "opened_date": "string (YYYY-MM-DD)",
          "closed_date": "string (YYYY-MM-DD, or null if never stated)",
          "channel": "string",
          "agent": "string",
          "issue_category": "string",
          "csat": "integer or null"
        },
        "order": {
          "ticket_id": "string",
          "order_id": "string or null",
          "product_name": "string or null",
          "region": "string",
          "fulfillment_center": "string or null",
          "carrier": "string or null",
          "payment_method": "string or null"
        },
        "resolution": {
          "ticket_id": "string",
          "outcome": "string",
          "refund_amount_usd": "number or null"
        }
      }

      **CONSTRAINED FIELDS — use exactly one of the listed values:**
      - issue_category: shipping_delay, return_request, warranty_claim,
        exchange_sizing, refund_status, duties_customs, lost_parcel,
        damaged_in_transit, product_question, payment_declined,
        address_change, order_cancellation
      - region: US West, US Midwest, US East, Canada, EU, UK, AU/NZ, Japan/SG
      - fulfillment_center: Reno NV, Harrisburg PA, Rotterdam NL
      - outcome: resolved, refunded, replaced, escalated, closed_no_action

      **CRUCIAL RULES:**
      - issue_category is never stated literally. Classify it from the content.
      - region is often not stated. Infer it from the destination city.
      - Use null where a value is genuinely absent. Never invent a value and
        never substitute 0 for a missing number.
      - Output ONLY the raw JSON object. No markdown fences, no commentary.

      Here is the case note:
      """,
      raw_text
    ) AS prompt
    FROM everstorm_data.raw_tickets_table
  ),
  STRUCT(0.2 AS temperature, 2048 AS max_output_tokens)
);
```

Three prompt decisions worth understanding: **constrain the label space**
(`issue_category` is classified, not extracted, and unconstrained it fragments
into near-duplicate labels); **ask for what is literally in the text**
(`closed_date` appears in the prose, `resolution_days` does not — derive it in
SQL); and **name null explicitly** (models substitute `0` otherwise, silently
corrupting averages).

### Normalise

```sql
CREATE OR REPLACE TABLE everstorm_data.tickets AS
WITH Cleaned AS (
  SELECT SAFE.PARSE_JSON(
    REGEXP_EXTRACT(
      JSON_VALUE(structured_data, '$.candidates[0].content.parts[0].text'),
      r'\{[\s\S]*\}')
  ) AS d
  FROM everstorm_data.structured_tickets
)
SELECT
  JSON_VALUE(d, '$.ticket.ticket_id')                      AS ticket_id,
  SAFE_CAST(JSON_VALUE(d, '$.ticket.opened_date') AS DATE) AS opened_date,
  SAFE_CAST(JSON_VALUE(d, '$.ticket.closed_date') AS DATE) AS closed_date,
  JSON_VALUE(d, '$.ticket.channel')                        AS channel,
  JSON_VALUE(d, '$.ticket.agent')                          AS agent,
  JSON_VALUE(d, '$.ticket.issue_category')                 AS issue_category,
  SAFE_CAST(JSON_VALUE(d, '$.ticket.csat') AS INT64)       AS csat
FROM Cleaned
WHERE d IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY opened_date) = 1;
```

```sql
CREATE OR REPLACE TABLE everstorm_data.orders AS
WITH Cleaned AS (
  SELECT SAFE.PARSE_JSON(
    REGEXP_EXTRACT(
      JSON_VALUE(structured_data, '$.candidates[0].content.parts[0].text'),
      r'\{[\s\S]*\}')
  ) AS d
  FROM everstorm_data.structured_tickets
)
SELECT
  JSON_VALUE(d, '$.order.ticket_id')          AS ticket_id,
  JSON_VALUE(d, '$.order.order_id')           AS order_id,
  JSON_VALUE(d, '$.order.product_name')       AS product_name,
  JSON_VALUE(d, '$.order.region')             AS region,
  JSON_VALUE(d, '$.order.fulfillment_center') AS fulfillment_center,
  JSON_VALUE(d, '$.order.carrier')            AS carrier,
  JSON_VALUE(d, '$.order.payment_method')     AS payment_method
FROM Cleaned
WHERE d IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY order_id) = 1;
```

```sql
CREATE OR REPLACE TABLE everstorm_data.resolutions AS
WITH Cleaned AS (
  SELECT SAFE.PARSE_JSON(
    REGEXP_EXTRACT(
      JSON_VALUE(structured_data, '$.candidates[0].content.parts[0].text'),
      r'\{[\s\S]*\}')
  ) AS d
  FROM everstorm_data.structured_tickets
)
SELECT
  JSON_VALUE(d, '$.resolution.ticket_id') AS ticket_id,
  JSON_VALUE(d, '$.resolution.outcome')   AS outcome,
  SAFE_CAST(JSON_VALUE(d, '$.resolution.refund_amount_usd') AS FLOAT64) AS refund_amount_usd
FROM Cleaned
WHERE d IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY ticket_id ORDER BY outcome) = 1;
```

### The payoff queries

```sql
-- Q1: slowest fulfilment centre  → Rotterdam
SELECT o.fulfillment_center, COUNT(*) AS tickets,
       ROUND(AVG(DATE_DIFF(t.closed_date, t.opened_date, DAY)), 1) AS avg_days
FROM everstorm_data.tickets t
JOIN everstorm_data.orders o USING (ticket_id)
WHERE t.closed_date IS NOT NULL AND o.fulfillment_center IS NOT NULL
GROUP BY 1 ORDER BY avg_days DESC;

-- Q2: warranty claims by product  → Summit GTX Hiking Boot
SELECT o.product_name, COUNT(*) AS warranty_claims,
       COUNTIF(r.outcome = 'replaced') AS replaced
FROM everstorm_data.tickets t
JOIN everstorm_data.orders o      USING (ticket_id)
JOIN everstorm_data.resolutions r USING (ticket_id)
WHERE t.issue_category = 'warranty_claim'
GROUP BY 1 ORDER BY warranty_claims DESC LIMIT 5;
```

These are calendar days; `eval/sql_eval.md` reports business days, so absolute
figures differ while the ranking holds.

---

## Part 2 — Semantic search inside BigQuery

```sql
CREATE OR REPLACE TABLE everstorm_data.chunked_tickets AS
WITH Numbered AS (
  SELECT ROW_NUMBER() OVER () AS doc_id, raw_text
  FROM everstorm_data.raw_tickets_table
)
SELECT doc_id,
       CONCAT(CAST(doc_id AS STRING), '-',
              CAST(ROW_NUMBER() OVER (PARTITION BY doc_id) AS STRING)) AS chunk_id,
       TRIM(chunk) AS chunk_text
FROM Numbered, UNNEST(SPLIT(raw_text, '.')) AS chunk
WHERE LENGTH(TRIM(chunk)) > 15;

CREATE OR REPLACE MODEL everstorm_data.text_embedding_model
REMOTE WITH CONNECTION `REPLACE-WITH-YOUR-FULL-CONNECTION-STRING`
OPTIONS (endpoint = 'text-embedding-005');

CREATE OR REPLACE TABLE everstorm_data.embedded_tickets AS
SELECT * FROM ML.GENERATE_EMBEDDING(
  MODEL everstorm_data.text_embedding_model,
  (SELECT doc_id, chunk_id, chunk_text AS content FROM everstorm_data.chunked_tickets),
  STRUCT('RETRIEVAL_DOCUMENT' AS task_type)
);
```

Run the keyword search **first** — it returns nothing, which is the point:

```sql
SELECT chunk_text FROM everstorm_data.chunked_tickets
WHERE LOWER(chunk_text) LIKE '%fell apart%';          -- zero rows

SELECT base.content, distance
FROM VECTOR_SEARCH(
  TABLE everstorm_data.embedded_tickets,
  'ml_generate_embedding_result',
  (SELECT ml_generate_embedding_result
   FROM ML.GENERATE_EMBEDDING(
     MODEL everstorm_data.text_embedding_model,
     (SELECT 'customers whose boots fell apart' AS content),
     STRUCT('RETRIEVAL_QUERY' AS task_type))),
  top_k => 5, distance_type => 'COSINE');
```

The top hit is *"the outsole has separated from the midsole across the
forefoot"* — no shared keywords with the query.

---

## Part 3 — Cloud SQL + pgvector

```bash
source ./set_env.sh
gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME

SERVICE_ACCOUNT_EMAIL=$(gcloud sql instances describe $INSTANCE_NAME \
  --format="value(serviceAccountEmailAddress)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/aiplatform.user"
```

In Cloud SQL Studio:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;

CREATE TABLE policy_chunks (
  id SERIAL PRIMARY KEY,
  chunk_content TEXT,
  embedding VECTOR(768)
);

-- Prove the round-trip by hand before automating it
SET session.my_search_var = 'Everstorm returns: 30 days from delivery, extended to 31 January for purchases made 1 November to 31 December.';
INSERT INTO policy_chunks (chunk_content, embedding)
VALUES (current_setting('session.my_search_var'),
        (embedding('text-embedding-005', current_setting('session.my_search_var')))::vector);

CREATE INDEX ON policy_chunks USING hnsw (embedding vector_cosine_ops);
```

---

## Part 4 — Dataflow vectorization

```bash
source ./set_env.sh
cd ~/everstorm-dataengineer/pipeline
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION=${REGION},_REPO_NAME=${REPO_NAME} .

cd ~/everstorm-dataengineer
python -m venv env
source env/bin/activate
pip install -r pipeline/requirements.txt
```

Fill the five `#REPLACE` markers in `pipeline/vectorize_kb_pipeline.py`
(reference: `solutions/pipeline_completed.py`), then validate locally:

```bash
cd pipeline
python3 vectorize_kb_pipeline.py \
  --runner=DirectRunner \
  --project=$PROJECT_ID --region=$REGION \
  --job_name="everstorm-local-test-$(date +%Y%m%d-%H%M%S)" \
  --temp_location="gs://${BUCKET_NAME}/dataflow/temp" \
  --staging_location="gs://${BUCKET_NAME}/dataflow/staging" \
  --input_pattern="gs://${BUCKET_NAME}/kb/*.md" \
  --instance_name=$INSTANCE_NAME
```

Then at scale:

```bash
python vectorize_kb_pipeline.py \
  --runner=DataflowRunner \
  --project=$PROJECT_ID --job_name=$DF_JOB_NAME \
  --temp_location="gs://${BUCKET_NAME}/dataflow/temp" \
  --staging_location="gs://${BUCKET_NAME}/dataflow/staging" \
  --sdk_container_image="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/everstorm-vectorizer:latest" \
  --sdk_location=container --experiments=use_runner_v2 \
  --input_pattern="gs://${BUCKET_NAME}/kb/*.md" \
  --instance_name=$INSTANCE_NAME --region=$REGION
```

```sql
SELECT COUNT(*) FROM policy_chunks;   -- 263 + your 1 manual row
```

---

## Part 5 — The agent

Fill the three `#REPLACE` markers in `support_agent/agent.py` (reference:
`solutions/agent_completed.py`), then:

```bash
cd ~/everstorm-dataengineer
source ./set_env.sh
source env/bin/activate
pip install -r support_agent/requirements.txt
adk run support_agent
```

Try, in this order:

1. `How long do I have to return something?` — baseline; watch the tool call fire
   before the answer
2. `What's the free shipping threshold?` — the superseded-revision trap ($75, not
   $99)
3. `I'm in the UK, do I pay import duty?` — the regional trap (DDU, not the EU's
   DDP)

### Deploy

```bash
source ./set_env.sh
cd ~/everstorm-dataengineer
gcloud builds submit . --project=${PROJECT_ID} --region=${REGION} \
  --substitutions=_AGENT_NAME=${AGENT_NAME},_IMAGE_PATH=${IMAGE_PATH}

gcloud run deploy ${SERVICE_NAME} \
  --image=${IMAGE_PATH} --platform=managed --region=${REGION} \
  --set-env-vars="A2A_HOST=0.0.0.0,A2A_PORT=8080" \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE" \
  --set-env-vars="GOOGLE_CLOUD_LOCATION=${REGION}" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},PUBLIC_URL=${PUBLIC_URL},REGION=${REGION}" \
  --set-env-vars="INSTANCE_NAME=${INSTANCE_NAME},KB_TABLE=${KB_TABLE}" \
  --set-env-vars="DB_USER=${DB_USER},DB_PASSWORD=${DB_PASSWORD},DB_NAME=${DB_NAME}" \
  --allow-unauthenticated --project=${PROJECT_ID} --min-instances=1
```

```bash
curl -s ${PUBLIC_URL}/.well-known/agent-card.json | jq .
```

---

## Cleanup

See the Cleanup section of `README.md`.
