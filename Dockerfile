# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /build

# System deps required at install time (build-essential for some native extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install the package and download the spaCy model into /install so it's
# easy to COPY into the runtime stage without carrying the build toolchain.
RUN pip install --no-cache-dir --prefix=/install . \
 && python -m spacy download en_core_web_sm --prefix /install

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

# Only the runtime system library is needed here
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages and the spaCy model from the builder
COPY --from=builder /install /usr/local

# Copy application source and migration files
COPY --from=builder /build/src ./src
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Persistent data (SQLite database + uploads) should be mounted here
VOLUME ["/data"]

ENV DATABASE_URL=sqlite:////data/kn0.db
ENV UPLOAD_DIR=/data/uploads
ENV SPACY_MODEL=en_core_web_sm

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["kn0", "--help"]
