"""
Performs the experimentation processing of a crawler experiment.
"""
import networkx as nx
import sys
from os.path import dirname, abspath


if __name__ == '__main__':
    sys.path.append(dirname(__file__))
    sys.path.append(abspath('./tribler'))

    from gumby.experiments.multichain.processing.DatabaseReader import SingleDatabaseReader
    data = SingleDatabaseReader("/home/norberhuis/workspace/outputbk/")
    data.database.close()
    nx.write_gexf(data.graph, "graph-crawler.gexf", encoding='utf8', prettyprint=False, version="1.2draft")