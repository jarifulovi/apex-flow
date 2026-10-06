# ==============================================================================
# Stage 1: Build & Dependencies Stage
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 2: Final Lightweight Production Runtime Stage
# ==============================================================================
FROM python:3.12-slim AS runtime

# Install runtime dependencies (curl for health check probe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create non-root application user for security
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app appuser

WORKDIR /app

# Create persistent storage directory with proper permissions
RUN mkdir -p /app/.apexflow_storage && chown -R appuser:appgroup /app

# Copy application code and migrations
COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup migrations /app/migrations

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production server execution command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
