#!/bin/bash
set -x
cur=$(pwd)
for val in "player"
do
    cd ${val}
    ./test-${val}.sh
    if [ "$?" != "0" ]
    then
        echo "test ${val} failed"
        exit 0
    fi
    cd ${cur}
done
echo "tests passed"