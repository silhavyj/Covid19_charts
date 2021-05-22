#!/bin/bash

docker stop covid19
docker run -d --rm -e TZ=Europe/Prague --name covid19 -p 178.79.144.81:8000:8000 covid19

