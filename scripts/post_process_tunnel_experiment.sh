#!/bin/bash

# Parse statistics about the tunnel community
gumby/experiments/tunnels/parse_tunnel_statistics.py .

# Run the regular Dispersy message extraction script
post_process_dispersy_experiment.sh
