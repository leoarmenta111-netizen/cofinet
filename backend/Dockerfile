# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements.txt requirements-payment.txt ./
RUN pip wheel --wheel-dir /wheels -r requirements.txt -r requirements-payment.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/cofinet/.local/bin:${PATH}"

RUN groupadd --system cofinet \
    && useradd --system --gid cofinet --create-home cofinet

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels
COPY --chown=cofinet:cofinet app ./app

USER cofinet
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS development
USER root
RUN pip install --no-cache-dir watchfiles==1.1.1
USER cofinet
