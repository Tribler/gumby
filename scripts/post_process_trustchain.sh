#!/usr/bin/env bash
gumby/experiments/trustchain/post_process_trustchain.py .

# Invoke the IPv8 experiment process which will also plot our TrustChain statistics
post_process_ipv8_experiment.sh
