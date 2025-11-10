#!/bin/bash

set -o errexit
set -o nounset

rm -f './celerybeat.pid'
celery -A synclias.celery_app worker -l info
