#!/usr/bin/env bash

set -x

aws s3 sync s3://tmdb-movies-json-with-all-details /chunks/

python ./tmdb.py