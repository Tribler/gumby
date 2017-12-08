#!/bin/bash

# Parse statistics about the market community
gumby/experiments/market/parse_market_statistics.py .

# Run the regular Dispersy message extraction script
post_process_dispersy_experiment.sh
