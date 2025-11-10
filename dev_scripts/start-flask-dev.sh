#!/bin/sh

flask db upgrade

flask run --debug
