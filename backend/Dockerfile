FROM python:3.14.10-slim-trixie AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /src
COPY pyproject.toml ./
RUN python -c "import pathlib, tomllib; project = tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']; pathlib.Path('requirements.txt').write_text('\n'.join(project['dependencies']) + '\n')" \
    && pip install --only-binary=:all: --requirement requirements.txt

COPY app ./app
RUN pip install --no-deps .

FROM python:3.14.10-slim-trixie

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FORWARDED_ALLOW_IPS=127.0.0.1 \
    WEB_CONCURRENCY=1

RUN groupadd --system --gid 10001 bodha \
    && useradd --system --uid 10001 --gid bodha --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin bodha

COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY alembic.ini docker-entrypoint.sh ./
COPY alembic ./alembic

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --start-interval=2s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]

ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
CMD ["api"]
