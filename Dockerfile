# =============================================================================
# Dockerfile - Tibia Ops Config Application
# =============================================================================
# The application uses only the Python standard library, so no build stage
# or pip installs are needed - a single slim stage keeps the image small.
# Demonstrates: containerization, security best practices
# =============================================================================

FROM python:3.13-slim AS production

# Security: Run as non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser .configs/ ./.configs/

# Switch to non-root user
USER appuser

ENV PYTHONUNBUFFERED=1

# Expose Prometheus metrics port
EXPOSE 8000

# Health check (use /health - it doesn't trigger API calls like /metrics does)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command - run the metrics server
CMD ["python", "scripts/metrics_server.py"]
