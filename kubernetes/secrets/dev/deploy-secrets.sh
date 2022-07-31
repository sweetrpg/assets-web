#!/bin/bash

set -e

ns=${1:-sweetrpg-support}

scriptdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

pushd ${scriptdir}

echo "Deleting old secrets..."
kubectl delete -n "${ns}" secret sweetrpg-registry assets-web-files assets-web-cache assets-web-auth assets-web-misc assets-web-common || true

echo "Docker registry config..."
# kubectl create -n "${ns}" secret docker-registry sweetrpg-registry \
#     --docker-server=registry.sweetrpg.com \
#     --docker-username=docker \
#     --docker-password=ESU7PnNtlt07zkvbnSyByrTdzllajxIQWqY7mswQR78
kubectl create -n "${ns}" secret docker-registry sweetrpg-registry \
    --docker-server=ghcr.io \
    --docker-username=paulyhedral \
    --docker-password=$(cat ${scriptdir}/tokens.txt | grep '^sweetrpg-registry' | cut -f2 -d:)
#kubectl create -n "${ns}" secret dockerconfigjson sweetrpg-registry \
#    --from-file=.dockerconfigjson

echo "NewRelic and logging config..."
kubectl create -n "${ns}" secret generic assets-web-files \
    --from-file=newrelic.ini

echo "Other secrets..."
kubectl create -n "${ns}" secret generic assets-web-cache \
    --from-env-file=cache.env
kubectl create -n "${ns}" secret generic assets-web-auth \
    --from-env-file=auth.env
kubectl create -n "${ns}" secret generic assets-web-misc \
    --from-env-file=misc.env
kubectl create -n "${ns}" secret generic assets-web-common \
    --from-env-file=../common.env

popd
