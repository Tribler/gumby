#!/bin/bash -xe

EXPECTED_ARGS=3
if [ $# -ne $EXPECTED_ARGS ]
then
	echo "Usage: `basename $0` reportName inputFile \"description\""
	exit 65
fi

OUTPUTDIR=$(readlink -f "$1")

mkdir -p $OUTPUTDIR

# Find the stp dir
SCRIPTDIR=$( dirname $(readlink -f "$0"))
if [ ! -d "$SCRIPTDIR" ]; then
    SCRIPTDIR=$( dirname $(readlink -f $(which "$0")))
fi
if [ ! -d "$SCRIPTDIR" ]; then
    echo "Couldn't find this script path, bailing out."
    exit 1
fi

$SCRIPTDIR/stap_preprocess_csv.sh $2

Rscript $SCRIPTDIR/r/io_writes_report.R $1 $2 "$3"

cd $SCRIPTDIR
python stap_make_io_writes_report.py $OUTPUTDIR
cp ../lib/templates/io_writes_report.css $OUTPUTDIR/io_writes_report.css
echo "Report created in $OUTPUTDIR ok"
