#!/bin/bash

# Parse statistics about the tunnel community
gumby/experiments/tunnels/parse_tunnel_statistics.py .

# Run the regular statistics extraction script
graph_process_guard_data.sh
