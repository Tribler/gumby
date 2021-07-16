#!/bin/bash
set -e

# TODO(emilon): Maybe move this to the general setup script
#make sure the R local install dir exists
mkdir -p $R_LIBS_USER
R --no-save --quiet < $R_SCRIPTS_PATH/install.r

for R_SCRIPT in ""$R_SCRIPTS_TO_RUN $EXTRA_R_SCRIPTS_TO_RUN; do
    if [ -e $EXPERIMENT_DIR/r/$R_SCRIPT ]; then
        R_SCRIPT_PATH=$EXPERIMENT_DIR/r/$R_SCRIPT
    else
        if [ -e $R_SCRIPTS_PATH/$R_SCRIPT ]; then
            R_SCRIPT_PATH=$R_SCRIPTS_PATH/$R_SCRIPT
        else
            echo "ERROR: $R_SCRIPT not found!"
            FAILED=5
        fi
    fi
    R --no-save --quiet --args $XMIN $XMAX $R_SCRIPT < $R_SCRIPT_PATH | tee ${R_SCRIPT}.log &
done

wait

exit $FAILED
