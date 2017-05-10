import os
import unittest

from scripts.post_process_historical_values import DroppedStatsProcessor


class TestDroppedStatsProcessor(unittest.TestCase):

    def setUp(self):
        super(TestDroppedStatsProcessor, self).setUp()
        self.historical_json = os.path.join(os.path.dirname(__file__),
                                            "data",
                                            "historical_data.json")
        self.in_irq_file = os.path.join(os.path.dirname(__file__),
                                        "data",
                                        "data_inside_irq.txt")
        self.out_irq_file = os.path.join(os.path.dirname(__file__),
                                         "data",
                                         "data_outside_irq.txt")

        with open(self.historical_json, "w") as f:
            f.write('{"complete.scenario": [3.5, 4.0, 5.0, 5.5, 4.5, 3.5], "incomplete.scenario": [1.0]}')

    def test_in_irq(self):
        os.environ["SCENARIO_FILE"] = "complete.scenario"

        processor = DroppedStatsProcessor(self.historical_json, self.in_irq_file)

        self.assertEqual(processor.process(), 0)

    def test_outside_irq(self):
        os.environ["SCENARIO_FILE"] = "complete.scenario"

        processor = DroppedStatsProcessor(self.historical_json, self.out_irq_file)

        self.assertEqual(processor.process(), 1)

    def test_not_enough_values(self):
        os.environ["SCENARIO_FILE"] = "incomplete.scenario"

        processor = DroppedStatsProcessor(self.historical_json, self.out_irq_file)

        self.assertEqual(processor.process(), 0)

    def test_no_input_file(self):
        os.environ["SCENARIO_FILE"] = "complete.scenario"

        processor = DroppedStatsProcessor(self.historical_json, "idontexist")

        self.assertEqual(processor.process(), 0)

    def test_no_scenario(self):
        if "SCENARIO_FILE" in os.environ:
            del os.environ["SCENARIO_FILE"]

        processor = DroppedStatsProcessor(self.historical_json, self.in_irq_file)

        self.assertEqual(processor.process(), 0)
