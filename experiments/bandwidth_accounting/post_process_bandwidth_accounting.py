#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from pony.orm import db_session

from tribler_core.components.bandwidth_accounting.db.database import BandwidthDatabase
from tribler_core.components.bandwidth_accounting.db.transaction import BandwidthTransactionData

from gumby.statsparser import StatisticsParser


class BandwidthStatisticsParser(StatisticsParser):
    """
    Parse TrustChain statistics after an experiment has been completed.
    """

    def __init__(self, node_directory):
        super().__init__(node_directory)
        self.output_dir = os.path.join(os.environ['PROJECT_DIR'], 'output')

    def aggregate_databases(self):
        transactions = []

        for _, filename, _ in self.yield_files('bandwidth.db'):
            print("Considering database %s" % os.path.abspath(filename))
            db = BandwidthDatabase(Path(os.path.abspath(filename)), None)
            with db_session:
                db_txs = list(db.BandwidthTransaction.select())
                for db_tx in db_txs:
                    tx = BandwidthTransactionData.from_db(db_tx)
                    transactions.append(tx)

        print("Found %d transactions..." % len(transactions))
        all_payouts_db = BandwidthDatabase(Path(self.output_dir) / "bandwidth.db", None)
        for tx in transactions:
            all_payouts_db.BandwidthTransaction.insert(tx)

        with open("total_payout_edges.txt", "w") as out_file:
            out_file.write("%d" % len(transactions))

    def run(self):
        self.aggregate_databases()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = BandwidthStatisticsParser(sys.argv[1])
parser.run()
