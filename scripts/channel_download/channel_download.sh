#!/usr/bin/env bash

#if [ -z "$OUTPUT_DIR" ]; then
#    echo 'ERROR: $OUTPUT_DIR variable not found, are you running this script from within gumby?'
#    exit 1
#fi
#
#if [ -z "$EXPERIMENT_DIR" ]; then
#    echo 'ERROR: EXPERIMENT_DIR variable not found, are you running this script from within gumby?'
#    exit 1
#fi

#cd $OUTPUT_DIR

echo "Running post channel downloading..."
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

MERGE_TSV_FILE="all.tsv"

# find .log file and put them to output/data
mkdir -p data

for log in $(grep -H -r "Dispersy configured" | grep -v ^Binary | cut -d: -f1)
do
    thedir=`dirname $log`
    log_=${log##*/}
    # the name will be logname_localhost_nodenumber.log
    fname="${log_%.*}_`echo ${thedir} | tr /. _`.log"
    cp $log "data/$fname"

    echo "copying $fname to data/"

    tname="${fname%.*}.tsv"

    python $SCRIPT_DIR/channel_dl_parse.py data/$fname > data/$tname
done

tsvlist=$(find . -regex ".*\.tsv")
echo -e "ts\tihash\tactor\tul_speed\tdl_speed\tul_tot\tdl_tot\tprogress\tavail\tdsavail" > $MERGE_TSV_FILE.raw

for tsvs in $tsvlist
do
    if [ `awk -F' ' '{print NF; exit}' $tsvs` -eq 10 ]; then
        tail -n +2 $tsvs >> $MERGE_TSV_FILE.raw
    fi
done
(head -n 1 $MERGE_TSV_FILE.raw && tail -n +2 $MERGE_TSV_FILE.raw | sort) > $MERGE_TSV_FILE.sorted

sort -k2 ihashname.txt | uniq > ihashname_unique.txt
mv ihashname_unique.txt ihashname.txt

$SCRIPT_DIR/channel_dl_proc.R all.tsv.sorted


# Create RData files for plotting from log files and crate image
convert -resize 25% -density 300 -depth 8 -quality 85 channel_dl_figure.pdf channel_dl_figure.png
rm -rf localhost/ tracker/ err.txt 2>&1
