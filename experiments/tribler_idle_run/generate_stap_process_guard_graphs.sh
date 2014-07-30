#!/bin/bash

stap_make_io_writes_report.sh $OUTPUT_DIR/report $OUTPUT_DIR/stap.csv "1H run report" 
graph_process_guard_data.sh
