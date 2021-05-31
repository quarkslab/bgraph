# Inspired from https://github.com/michael0liver/python-poetry-docker-example

FROM ubuntu:18.04 as git-builder
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    make \
    libssl-dev \
    libghc-zlib-dev \
    libcurl4-openssl-dev \
    libexpat1-dev \
    gettext \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

RUN wget https://github.com/git/git/archive/v2.29.3.zip -O git.zip && \
    unzip git.zip && \
    cd git-* && \
    make -j prefix=/usr && \
    make prefix=/usr install

FROM python:3.8-slim as python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    PYTHONIOENCODING=utf-8
ENV PATH="${POETRY_HOME}/bin:${VENV_PATH}/bin:${PATH}"

RUN useradd -m user && \
    mkdir -p /opt/repo ${PYSETUP_PATH} && \
    chown -R user: /opt/repo ${PYSETUP_PATH}

FROM python-base as builder-base
RUN apt-get update && apt-get upgrade -y && apt-get install --no-install-recommends -y \
    ca-certificates \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=1.1.4

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 && \
    curl -sSL https://storage.googleapis.com/git-repo-downloads/repo > /opt/repo/repo && \
    chmod a+x /opt/repo/repo /opt/poetry/bin/poetry

USER user
WORKDIR $PYSETUP_PATH

COPY ./poetry.lock ./pyproject.toml ./
RUN poetry install --no-dev

#FROM python-base as development
#COPY --from=builder-base $POETRY_HOME $POETRY_HOME
#COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH
#COPY --from=builder-base /opt/repo/repo /opt/repo/repo
#COPY --from=git-builder /usr/bin/git /usr/local/bin/git
#
#USER user
#WORKDIR /home/user
#COPY --chown=user:user . .
#RUN poetry install
#
#ENTRYPOINT ["poetry"]
#CMD ["run", "ipython"]


FROM python-base as production
COPY --from=builder-base $VENV_PATH $VENV_PATH
COPY --from=builder-base /opt/repo/repo /opt/repo/repo
COPY --from=git-builder /usr/bin/git /usr/local/bin/git
COPY --from=git-builder /usr/libexec/git-core/ /usr/libexec/git-core

ENV PATH="/opt/repo/:${PATH}"

RUN apt-get update && apt-get upgrade -y && apt-get install --no-install-recommends -y \
    libcurl4 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /usr/share/git-core/templates

USER user
WORKDIR /home/user
COPY --chown=user:user . .
RUN "${VENV_PATH}/bin/pip" install . && \
    chmod +x /home/user/docker/entrypoint.sh

ENTRYPOINT ["/home/user/docker/entrypoint.sh"]
CMD ["bgraph", "--help"]