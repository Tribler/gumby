#!/bin/bash

EXPECTED_ARGS=3
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` reportName inputFile \"description\""
	exit 65
fi

OUTPUTDIR=../output/perf_reports

mkdir -p $OUTPUTDIR/$1
Rscript r/IOWritesReport.R $1 $2 "$3"

python make_io_writes_report.py $1
cp ../templates/io_writes_report.css $OUTPUTDIR/$1/io_writes_report.css
echo "Report created in $OUTPUTDIR/$1 ok"
