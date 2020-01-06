#!/usr/bin/env python3
import json
import os
import sys

from gumby.statsparser import StatisticsParser


class MarketStatisticsParser(StatisticsParser):
    """
    This class is responsible for parsing statistics of the market community
    """

    def __init__(self, node_directory):
        super(MarketStatisticsParser, self).__init__(node_directory)
        self.total_quantity_traded = 0
        self.total_payment = 0
        self.total_ask_quantity = 0
        self.total_bid_quantity = 0
        self.avg_order_latency = 0

    def aggregate_transaction_data(self):
        """
        Aggregate all transaction data during the experiment
        """
        transactions_str = ""
        transactions_cumulative_str = "0,0\n"
        transactions_times = []

        for peer_nr, filename, dir in self.yield_files('transactions.log'):
            transactions = [line.rstrip('\n') for line in open(filename)]
            for transaction in transactions:
                parts = transaction.split(',')
                self.total_quantity_traded += float(parts[2])
                self.total_payment += float(parts[1]) * float(parts[2])
                transactions_str += transaction + '\n'
                transactions_times.append(float(parts[0]))

        transactions_times = sorted(transactions_times)
        total_transactions = 0
        for transaction_time in transactions_times:
            total_transactions += 1
            transactions_cumulative_str += str(transaction_time) + "," + str(total_transactions) + "\n"

        with open('transactions.log', 'w') as transactions_file:
            transactions_file.write("time,price,quantity,payments,peer1,peer2\n")
            transactions_file.write(transactions_str)

        with open('transactions_cumulative.csv', 'w') as transactions_file:
            transactions_file.write("time,transactions\n")
            transactions_file.write(transactions_cumulative_str)

    def aggregate_order_data(self):
        """
        Aggregate all data of the orders
        """
        orders_str = "time,id,peer,is_ask,completed,price,quantity,reserved_quantity,traded_quantity,completed_time\n"
        orders_data_all = ""

        for peer_nr, filename, dir in self.yield_files('orders.log'):
            with open(filename) as order_file:
                orders_data = order_file.read()
                orders_str += orders_data
                orders_data_all += orders_data

        with open('orders.log', 'w') as orders_file:
            orders_file.write(orders_str)

        # Calculate the average order latency
        sum = 0
        amount = 0

        for line in orders_data_all.split('\n'):
            if len(line) == 0:
                continue

            parts = line.split(',')
            if parts[4] == "complete":
                sum += float(parts[9]) - float(parts[0])
                amount += 1

            if parts[3] == "ask":
                self.total_ask_quantity += float(parts[6])
            else:
                self.total_bid_quantity += float(parts[6])

        if amount > 0:
            self.avg_order_latency = float(sum) / float(amount)

    def aggregate_general_stats(self):
        """
        Aggregate general statistics for each peer
        """
        total_asks = 0
        total_bids = 0
        fulfilled_asks = 0
        fulfilled_bids = 0

        for peer_nr, filename, dir in self.yield_files('market_stats.log'):
            with open(filename) as stats_file:
                stats_dict = json.loads(stats_file.read())
                total_asks += stats_dict['asks']
                total_bids += stats_dict['bids']
                fulfilled_asks += stats_dict['fulfilled_asks']
                fulfilled_bids += stats_dict['fulfilled_bids']

        with open('aggregated_market_stats.log', 'w') as stats_file:
            stats_dict = {'asks': total_asks, 'bids': total_bids,
                          'fulfilled_asks': fulfilled_asks, 'fulfilled_bids': fulfilled_bids,
                          'total_quantity_traded': self.total_quantity_traded,
                          'total_payment': self.total_payment,
                          'avg_order_latency': self.avg_order_latency,
                          'total_ask_quantity': int(self.total_ask_quantity),
                          'total_bid_quantity': int(self.total_bid_quantity)}
            stats_file.write(json.dumps(stats_dict))

    def run(self):
        self.aggregate_transaction_data()
        self.aggregate_order_data()
        self.aggregate_general_stats()


# cd to the output directory
os.chdir(os.environ['OUTPUT_DIR'])

parser = MarketStatisticsParser(sys.argv[1])
parser.run()
