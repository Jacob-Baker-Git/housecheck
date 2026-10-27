FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY housecheck ./housecheck
COPY data ./data
RUN pip install --no-cache-dir .
ENV HOUSECHECK_RUNS_DIR=/app/runs HOUSECHECK_WORLD_DB=/app/.worldmodel/world.sqlite
EXPOSE 8000
# Zetaris and Nightshift run on the host: point ZETARIS_REST_URL / METERLESS_BASE_URL at host.docker.internal
CMD ["housecheck", "serve", "--host", "0.0.0.0", "--port", "8000"]
