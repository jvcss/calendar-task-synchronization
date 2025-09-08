#!/bin/bash

PYTHON=$1
PYTHON_SCRIPT=$2
CONFIG_FILES_FOLDER=$3

for file in $3/*.ini
do
    $1 $2 "$file" >> test.log
done
