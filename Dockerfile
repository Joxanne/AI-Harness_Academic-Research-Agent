FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir \
    chainlit \
    google-generativeai \
    chromadb \
    arxiv \
    requests \
    python-dotenv \
    sentence-transformers

# Pre-download embedding model so startup is instant (baked into image)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Copy source
COPY . .

# HuggingFace Spaces requires port 7860
EXPOSE 7860

ENV CHAINLIT_HOST=0.0.0.0
ENV CHAINLIT_PORT=7860

CMD ["chainlit", "run", "src/app.py", "--host", "0.0.0.0", "--port", "7860"]
