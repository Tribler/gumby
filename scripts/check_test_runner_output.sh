#!/bin/bash
if [[ $# -gt 0 ]]; then
    folder="$1"
else
    folder=.
fi
pattern=".*/[0-9]+\\.err"
for f in `find $folder -regex $pattern`; do
    exit_status=$(tail -1 $f | grep -o "[0-9]*")
    if [[ ! -z $exit_status ]]; then
        file_name=$(grep -o "/[0-9][0-9]*\.err" <<< $f)
        proc_num=$(grep -o "[0-9][0-9]*" <<< $file_name)
        echo "Process $proc_num failed with exit status: $exit_status!"
        exit $exit_status
    fi
done
