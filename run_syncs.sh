#!/bin/bash

cd $(dirname $0)

for file in ./config_files/*.ini
do
    ./main.py "$file"
done
