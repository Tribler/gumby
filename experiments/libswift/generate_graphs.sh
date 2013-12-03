#!/bin/bash -xe

# TODO(emilon): Maybe move this to the general setup script
#make sure the R local install dir exists
mkdir -p $R_LIBS_USER
R --no-save --quiet < $R_SCRIPTS_PATH/install.r
graph_process_guard_data.sh


