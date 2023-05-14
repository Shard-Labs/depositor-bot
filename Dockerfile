FROM python:3.9.16-slim-bullseye as base

RUN apt-get update && apt-get install -y --no-install-recommends -qq gcc=4:10.2.1-1 libffi-dev=3.3-6 g++=4:10.2.1-1 curl \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

FROM base as builder

ENV POETRY_VERSION=1.4.2
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

COPY pyproject.toml poetry.lock ./
RUN poetry install

FROM base as production

COPY --from=builder /app /app
COPY . /app

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
    CMD curl -f http://localhost:8080/healthcheck || exit 1

CMD ["brownie run depositor"]