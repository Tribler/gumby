#!/usr/bin/env bash
gumby/experiments/bandwidth_accounting/post_process_bandwidth_accounting.py .

# Run the regular statistics extraction script
graph_process_guard_data.sh
