#!/usr/bin/env python2
"""
Performs database aggregation after a trustchain experiment.
"""
import os
import sys

if __name__ == '__main__':
    # Fix the path
    sys.path.append(os.environ['PROJECT_DIR'])
    sys.path.append(os.path.join(os.environ['PROJECT_DIR'], 'tribler'))
    sys.path.append(os.path.join(os.environ['PROJECT_DIR'], 'gumby', 'experiments', 'trustchain'))

    # Create output dir
    aggregation_path = os.path.join(os.environ['PROJECT_DIR'], 'output', 'sqlite')
    if not os.path.exists(aggregation_path):
        os.makedirs(aggregation_path)

    from database_reader import GumbyDatabaseAggregator

    data = GumbyDatabaseAggregator(os.path.join(os.environ['PROJECT_DIR'], 'output'))
    data.combine_databases()
    data.generate_block_file()
    data.database.close()
