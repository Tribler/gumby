"""
Performs the experimentation processing of a gumby experiment.
"""
import networkx as nx


if __name__ == '__main__':
    sys.path.append(dirname(__file__))
    sys.path.append(abspath('./tribler'))

    from gumby.experiments.multichain.processing.DatabaseReader import GumbyDatabaseReader
    data = GumbyDatabaseReader("/home/norberhuis/workspace/output/")
    data.database.close()
