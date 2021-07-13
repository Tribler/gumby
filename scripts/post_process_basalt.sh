#!/bin/bash

# Parse statistics about the Basalt community
gumby/experiments/basalt/parse_basalt_statistics.py .

# Invoke the IPv8 experiment process which will also plot our Basalt statistics
post_process_ipv8_experiment.sh
