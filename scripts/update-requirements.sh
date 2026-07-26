#!/bin/bash

set -e

scriptdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

pushd ${scriptdir}/..

for r in app docs tests dev deploy; do
    echo ""
    echo "----------------------------"
    echo -e "Requirement: \033[1m${r}\033[0m"
    uv pip compile -U requirements/${r}.in -o requirements/${r}.txt
done

popd
