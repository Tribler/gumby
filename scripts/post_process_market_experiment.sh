#!/bin/bash

# Parse statistics about the market community
gumby/experiments/market/parse_market_statistics.py .

# Run the regular process guard script
graph_process_guard_data.sh
