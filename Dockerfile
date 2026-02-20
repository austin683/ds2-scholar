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

# db/ is intentionally NOT copied — Railway mounts a persistent volume here
# On first boot, get_index() will build it from knowledge_base/ automatically

ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
