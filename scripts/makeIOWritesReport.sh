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

python generate_IOWrites_report.py $1
echo "Report created in $OUTPUTDIR/$1 ok"
