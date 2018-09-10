#!/bin/bash

# Parse IPv8 statistics
gumby/experiments/ipv8/parse_ipv8_statistics.py .
graph_ipv8_stats.sh

# Run the regular process guard script
graph_process_guard_data.sh
