FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer — only reruns if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the BGE model into the image so cold starts don't re-download it
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# Copy source and knowledge base into the image
COPY backend/ ./backend/
COPY knowledge_base/ ./knowledge_base/

# Bake the pre-built ChromaDB index into the image as db_baked/.
# On startup, get_index() copies db_baked/ → db/ if the volume is empty or
# has an incompatible schema, avoiding an 8-hour runtime rebuild.
COPY db/ ./db_baked/

ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
