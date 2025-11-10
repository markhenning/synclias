#!/bin/bash

## Copy files from "locker" to shared storage

for FILE in `echo asn_db asn_names`; do
if [ ! -f $FILE ]; then
  cp locker/$FILE shared/
fi
done

set -o errexit
set -o nounset

## DB Upgrade
flask db upgrade

## Start app
gunicorn "synclias:create_app()" -k gthread --bind 0.0.0.0:8000 --access-logfile - --error-logfile - --timeout 90
