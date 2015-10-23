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
    print sys.argv
    if len(sys.argv) > 1:
        working_directory = sys.argv[1]

    from gumby.experiments.multichain.processing.DatabaseReader import SingleDatabaseReader
    print working_directory
    data = SingleDatabaseReader(working_directory)
    data.database.close()