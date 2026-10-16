FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_PATH=/data/flight-tracker.db

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install .

RUN useradd --create-home app && mkdir /data && chown app /data
USER app

VOLUME ["/data"]

CMD ["python", "-m", "flight_tracker"]
