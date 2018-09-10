#!/bin/bash

# Parse statistics about the market community
gumby/experiments/market/parse_market_statistics.py .

# Invoke the IPv8 experiment process which will also plot our market statistics
post_process_ipv8_experiment.sh
