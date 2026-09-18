# Dataflow worker image for the Everstorm knowledge-base vectorization pipeline.
# Baking dependencies into the image means workers start almost immediately
# instead of pip-installing on every cold start.
FROM gcr.io/dataflow-templates-base/python312-template-launcher-base

WORKDIR /dataflow

ENV GOOGLE_GENAI_USE_VERTEXAI=TRUE
ARG GOOGLE_CLOUD_PROJECT
ARG GOOGLE_CLOUD_LOCATION
ENV GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
ENV GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}

# Copy requirements first -- Docker layer caching means this step is only
# re-run when the dependency list actually changes.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Only read when launching as a Flex Template. We launch directly against the
# pipeline file with --sdk_container_image, so this is informational -- but it
# points at the real filename, unlike the upstream template it came from.
ENV FLEX_TEMPLATE_PYTHON_PY_FILE=vectorize_kb_pipeline.py
