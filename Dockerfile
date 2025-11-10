FROM python:3.14-slim-trixie
LABEL maintainer="Mark Henning <mcsmiggins@outlook.com>"

ARG UID=1000
ARG GID=1000

ARG FLASK_ENV="production"
ARG APP_HOME="/app"
ARG APP_USER="synclias"
ENV FLASK_ENV="${FLASK_ENV}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONAPP_HOMETWRITEBYTECODE=1

ENV FLASK_ENV="${FLASK_ENV}"

RUN apt-get update \
  && apt-get install -y build-essential \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get purge -y --auto-remove\
  && apt-get clean 

RUN mkdir ${APP_HOME}
WORKDIR ${APP_HOME}

RUN addgroup --system ${APP_USER} && adduser --system --group ${APP_USER}

COPY requirements.txt ${APP_HOME}
RUN pip install -r ${APP_HOME}/requirements.txt

COPY . ${APP_HOME}

RUN chown -R ${APP_USER}:${APP_USER} $APP_HOME

USER ${APP_USER}
ENV FLASK_APP="synclias"
CMD [ "/app/start-gunicorn.sh" ]
