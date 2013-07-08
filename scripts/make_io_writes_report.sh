#!/bin/bash

EXPECTED_ARGS=3
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` reportName inputFile \"description\""
	exit 65
fi

OUTPUTDIR=../output/perf_reports

mkdir -p $OUTPUTDIR/$1

# Find the stp dir
SCRIPTDIR=$( dirname $(readlink -f "$0"))
if [ ! -d "$SCRIPTDIR" ]; then
    SCRIPTDIR=$( dirname $(readlink -f $(which "$0")))
fi
if [ ! -d "$SCRIPTDIR" ]; then
    echo "Couldn't find this script path, bailing out."
    exit 1
fi

Rscript $SCRIPTDIR/r/io_writes_report.R $1 $2 "$3"

python $SCRIPTDIR/make_io_writes_report.py $1
cp $SCRIPTDIR/../templates/io_writes_report.css $OUTPUTDIR/$1/io_writes_report.css
echo "Report created in $OUTPUTDIR/$1 ok"
