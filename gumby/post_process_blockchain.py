from gumby.statsparser import StatisticsParser


class BlockchainTransactionsParser(StatisticsParser):
    """
    This class parsers blockchain transactions.
    """

    def __init__(self, node_directory):
        super(BlockchainTransactionsParser, self).__init__(node_directory)
        self.transactions = []
        self.cumulative_stats = []
        self.avg_latency = -1
        self.avg_start_time = 0

    def parse(self):
        """
        Parse all blockchain statistics.
        """
        self.compute_avg_start_time()
        self.parse_transactions()
        self.compute_avg_latency()
        self.compute_tx_cumulative_stats()
        self.write_all()

    def compute_avg_start_time(self):
        avg_start_time = 0
        num_files = 0
        for peer_nr, filename, dir in self.yield_files('submit_tx_start_time.txt'):
            with open(filename) as submit_tx_start_time_file:
                start_time = int(submit_tx_start_time_file.read())
                avg_start_time += start_time
                num_files += 1

        self.avg_start_time = int(avg_start_time / num_files)

    def parse_transactions(self):
        """
        This method should be implemented by the sub-class since it depends on the individual blockchain
        implementations. The execution of this method should fill the self.transactions array with information.
        """
        pass

    def compute_avg_latency(self):
        """
        Compute the average transaction latency.
        """
        avg_latency = 0
        num_comfirmed = 0
        for transaction in self.transactions:
            if transaction[4] != -1:
                avg_latency += transaction[4]
                num_comfirmed += 1

        self.avg_latency = avg_latency / num_comfirmed

    def compute_tx_cumulative_stats(self):
        """
        Compute cumulative transaction statistics.
        """
        submit_times = []
        confirm_times = []
        for transaction in self.transactions:
            submit_times.append(transaction[2])
            if transaction[3] != -1:
                confirm_times.append(transaction[3])

        submit_times = sorted(submit_times)
        confirm_times = sorted(confirm_times)

        cumulative_window = 100  # milliseconds
        cur_time = 0
        submitted_tx_index = 0
        confirmed_tx_index = 0

        submitted_count = 0
        confirmed_count = 0
        self.cumulative_stats = [(0, 0, 0)]

        while cur_time < max(submit_times[-1], confirm_times[-1]):
            # Increase counters
            while submitted_tx_index < len(submit_times) and submit_times[submitted_tx_index] <= cur_time + cumulative_window:
                submitted_tx_index += 1
                submitted_count += 1

            while confirmed_tx_index < len(confirm_times) and confirm_times[confirmed_tx_index] <= cur_time + cumulative_window:
                confirmed_tx_index += 1
                confirmed_count += 1

            cur_time += cumulative_window
            self.cumulative_stats.append((cur_time, submitted_count, confirmed_count))

    def write_all(self):
        """
        Write all information to disk.
        """
        with open("transactions.txt", "w") as transactions_file:
            transactions_file.write("peer_id,tx_id,submit_time,confirm_time,latency\n")
            for transaction in self.transactions:
                transactions_file.write("%d,%s,%d,%d,%d\n" % transaction)

        with open("tx_cumulative.csv", "w") as out_file:
            out_file.write("time,submitted,confirmed\n")
            for result in self.cumulative_stats:
                out_file.write("%d,%d,%d\n" % result)

        with open("latency.txt", "w") as latency_file:
            latency_file.write("%f" % self.avg_latency)
