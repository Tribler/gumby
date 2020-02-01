#!/usr/bin/env bash
gumby/experiments/trustchain/post_process_trustchain.py .

# Run the regular statistics extraction script
graph_process_guard_data.sh
