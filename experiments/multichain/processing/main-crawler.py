"""
Performs the experimentation processing of a crawler experiment.
"""
import sys
import os

if __name__ == '__main__':
    # Fix the path
    sys.path.append(os.path.abspath('./tribler'))
    sys.path.append(os.getcwd())

    working_directory = os.path.abspath("output/")
    if len(sys.argv) > 1:
        working_directory = sys.argv[1]

    from experiments.multichain.processing.DatabaseReader import SingleDatabaseReader
    data = SingleDatabaseReader(working_directory)
    data.database.close()