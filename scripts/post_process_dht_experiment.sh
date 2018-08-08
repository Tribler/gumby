#!/bin/bash

# Parse statistics about the dht community
gumby/experiments/dht/parse_dht_statistics.py .

graph_process_guard_data.sh
