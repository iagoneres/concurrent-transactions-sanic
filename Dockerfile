FROM python:3.11.8-slim

WORKDIR /app

COPY ./src /app/
COPY poetry.lock pyproject.toml /app/

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi && \
    rm -rf /root/.cache/pip

RUN useradd sanic --no-user-group --no-create-home --uid 1000 && \
    chown -R sanic /app

USER sanic

EXPOSE 8000

CMD ["python", "server.py"]
