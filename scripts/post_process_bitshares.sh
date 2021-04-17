#!/bin/bash

# Parse statistics about the market community
gumby/experiments/bitshares/parse_bitshares_statistics.py .

# Run the regular process guard script
graph_process_guard_data.sh
