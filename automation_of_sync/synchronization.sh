#!/bin/bash

PYTHON_SCRIPT=$1
CONFIG_FILES_FOLDER=$2

for file in $2/*.ini
do
    python3 $1 "$file" >> test.log
done

