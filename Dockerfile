FROM python:3.12.1-alpine

ENV POETRY_VERSION=1.7.1

RUN apk update && apk add gcc musl-dev libffi-dev
RUN addgroup -S dev && adduser -S dev -G dev

USER dev

RUN pip3 install --upgrade pip

ADD --chown=dev:dev poetry.lock pyproject.toml /home/dev/asterisk-prometheus-exporter/
WORKDIR /home/dev/asterisk-prometheus-exporter/
ENV PATH="/home/dev/.local/bin/:${PATH}"

RUN pip3 install --user "poetry==$POETRY_VERSION"
RUN poetry install --only main

ADD --chown=dev:dev src ./src
CMD ["poetry", "run", "python", "src/main.py"]

EXPOSE 8080
