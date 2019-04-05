import unittest

from gumby.scenario import ScenarioRunner


class TestForLoop(unittest.TestCase):
    """
    Test class which evaluates the correctness of the scenario language for loop implementation
    """

    def setUp(self):
        super(TestForLoop, self).setUp()
        self.scenario_parser = ScenarioRunner()
        self.scenario_parser._peernumber = 1
        self.callables = {
            'echo_values': self.echo_values,
            'store': self.store
        }
        self.local_storage = {}

    def set_variable(self, name, value):
        """
        Sets a scenario variable.

        :param name: the name of the variable
        :param value: the value of the variable
        """
        self.scenario_parser.user_defined_vars[name] = str(value)

    def echo_values(self, val, vval=None, cst=None):
        """
        This method will return a list containing four elements: the literal 'Proof' and the method's three parameters.

        :param val: an unnamed parameter which can have any arbitrary value
        :param vval: a named parameter which can have any arbitrary value
        :param cst: a named parameter which can have any arbitrary value
        :return: a list containing four elements: the literal 'Proof' and the method's three parameters
        """
        return ["Proof", val, vval, cst]

    def store(self, key, value):
        """
        Store a value in a test's local storage.

        :param key: the key under which the value is stored
        :param value: the value
        :return: None
        """
        self.local_storage[key] = value

    def execution_wrapper(self, command_line, peerspec="", line_number=1, test_file="test.file"):
        """
        Wraps the execution of a scenario command line. This method mimics what a scenario runner will actually do
        with a command line.

        :param command_line: the command line which will be executed
        :param peerspec: the command line's peer specification
        :param line_number: the line number
        :param test_file: the file name from which the command line stems
        :return: a list containing the returned values (as lists) of the executed command. There may be multiple
                 values returned since the command line may be unwrapped in multiple commands
        """
        unwrapped_lines = self.scenario_parser._parse_scenario_line(test_file, line_number, command_line, peerspec)

        if not unwrapped_lines:
            return []

        returned_values = []

        for _, _, _, clb, args, kwargs in unwrapped_lines:
            returned_values.append(self.callables[clb](*args, **kwargs))

        return returned_values

    def test_correct_for_loop_increasing(self):
        """
        Test a for loop with unit increments.
        """
        ground_truth = []
        for i in [str(x) for x in range(1, 11)]:
            ground_truth.append(['Proof', i, i, 'should_be_constant'])

        returned_values = self.execution_wrapper("@! for i in 1 to 10 call echo_values $i vval=$i "
                                                 "cst=should_be_constant")

        self.assertEqual(returned_values, ground_truth, 'The returned results is not as expected')

    def test_correct_for_loop_decreasing(self):
        """
        Test a for loop with unit decrements.
        """
        ground_truth = []
        for i in [str(x) for x in range(10, 0, -1)]:
            ground_truth.append(['Proof', i, i, 'should_be_constant'])

        returned_values = self.execution_wrapper("@! for i in 10 to 1 call echo_values $i vval=$i "
                                                 "cst=should_be_constant")

        self.assertEqual(returned_values, ground_truth, 'The returned results is not as expected')

    def test_for_loop_variable_replacement(self):
        """
        Test the correctness of variable replacement
        """
        self.execution_wrapper("@! for i in 1 to 5 call store $i constant_value")

        self.assertEqual([str(x) for x in range(1, 6)], sorted(self.local_storage.keys()),
                         "The key set must be equal to ['1', '2', ..., '5'] when sorted")

    def test_for_loop_peerspec_included(self):
        """
        Test that a peerspec is able to correctly identify if the current node should execute an iteration.
        """
        self.execution_wrapper("@! for i in 1 to 5 call store some_key $i", peerspec="$i")

        self.assertTrue(len(self.local_storage) == 1 and "some_key" in self.local_storage
                        and self.local_storage["some_key"] == '1', "The locally stored entry should be the ID "
                                                                   "of this peer (i.e. should be '1')")

    def test_for_loop_peerspec_excluded(self):
        """
        Test that a peerspec is able to correctly identify if the current node should not execute an iteration.
        """
        self.execution_wrapper("@! for i in 10 to 5 call store some_key $i", peerspec="$i")

        self.assertFalse(self.local_storage, "The local storage should be empty.")

    def test_for_loop_peerspec_static_included(self):
        """
        Test that a peerspec is able to correctly identify if the current node should execute an iteration when it's
        static and refers the peer's ID.
        """
        self.execution_wrapper("@! for i in 1 to 5 call store $i some_value", peerspec="1")

        self.assertEqual([str(x) for x in range(1, 6)], sorted(self.local_storage.keys()),
                         "The key set must be equal to ['1', '2', ..., '5'] when sorted")

    def test_for_loop_peerspec_static_excluded(self):
        """
        Test that a peerspec is able to correctly identify if the current node should execute an iteration when it's
        static and does not refer the peer's ID.
        """
        self.execution_wrapper("@! for i in 1 to 5 call store $i some_value", peerspec="2")

        self.assertFalse(self.local_storage, "The local storage should be empty")

    def test_for_loop_with_variables(self):
        """
        Test that a for loop which uses variables, that conflict in name with the control variable, the still works
        but the values swapped will be that of the variable.
        """
        self.set_variable("i", "constant_key_value")
        self.execution_wrapper("@! for i in 1 to 5 call store $i some_value")

        self.assertTrue(len(self.local_storage) == 1 and self.local_storage["constant_key_value"] == "some_value",
                        "There should be only one key - value pair in local storage: constant_key_value -> some_value")

    def test_for_loop_erroneous_peerspec(self):
        """
        Test the for loop when there is an erroneously specified peerspec.
        """
        self.set_variable('i', '1')
        self.assertFalse(
            self.execution_wrapper("@! for my_var in 1 to 10 call echo_values 'Should not work  - $i'", peerspec="$i"),
            "The command line should not return anything")

        self.assertFalse(
            self.execution_wrapper("@! for my_var in 1 to 10 call echo_values 'Should not work  - $i'", peerspec="$j"),
            "The command line should not return anything")

        self.assertFalse(
            self.execution_wrapper("@! for my_var in 1 to 10 call echo_values 'Should not work  - $i'", peerspec="$"),
            "The command line should not return anything")

    def test_wrong_for_loop_syntax(self):
        """
        Test the for loop when its syntax is wrong. These should silently fail, however, in real scenarios, they will
        output their errors to the event logger.
        """
        self.assertFalse(
            self.execution_wrapper("@! for my_var 1 to 10 call echo_values 'Will not work'"),
            "This command line should silently fail, and return nothing")

        self.assertFalse(
            self.execution_wrapper("@! for my_var in 1 10 call echo_values 'Will not work'"),
            "This command line should silently fail, and return nothing")

        self.assertFalse(
            self.execution_wrapper("@! for my_var in 1 to call echo_values 'Will not work'"),
            "This command line should silently fail, and return nothing")

        self.assertFalse(
            self.execution_wrapper("@! for my_var in to 10 call echo_values 'Will not work'"),
            "This command line should silently fail, and return nothing")

    def test_for_loop_peerspec_exclusion(self):
        """
        Test the for loop when it features peer exclusions. These are not supported yet, thus nothing should happen.
        """
        self.assertFalse(
            self.execution_wrapper("@! for i in 1 to 10 call echo_values 'Will not work'", peerspec="!3")
        )

    def test_peerspec_variable_outside_for(self):
        """
        Test the usage of a variable inside a peerspec outside of a for. This should be illegal, and should fail
        silently, even if the variable is set.
        """
        self.set_variable("i", "1")
        self.assertFalse(
            self.execution_wrapper("@! echo_values 'Will not work'", peerspec="$i"),
            "The command should fail silently, and should not return anything"
        )
