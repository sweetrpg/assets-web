#!/bin/bash

set -e

docker build -t registry.sweetrpg.com/sweetrpg-assets-web:latest .
docker push registry.sweetrpg.com/sweetrpg-assets-web
