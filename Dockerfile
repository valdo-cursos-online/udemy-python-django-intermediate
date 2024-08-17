FROM python:3.11.9-alpine3.20

LABEL maintainer="oh"

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt

ARG DEV=false
RUN python -m venv /py && \
    source /py/bin/activate && \
    /py/bin/pip install --upgrade pip && \
    apk add --update --no-cache postgresql-client build-base postgresql-dev musl-dev && \
    apk add --update --no-cache --virtual .tmp-build-deps \
      build-base postgresql-dev musl-dev && \
    /py/bin/pip install -r /tmp/requirements.txt && \
    if [ $DEV = "true" ]; \
      then /py/bin/pip install -r /tmp/requirements.dev.txt; \
    fi && \
    rm -rf /tmp && \
    apk del .tmp-build-deps && \
    adduser \
      --disabled-password \
      --no-create-home \
      django-user

COPY ./app .

EXPOSE 8002

ENV PATH="/py/bin:$PATH"

USER django-user