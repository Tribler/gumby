"""
Test the import functionality of experiment.py
"""
import logging
import os
import sys
import types
import unittest

from gumby.experiment import ExperimentClient

logging.basicConfig(level="CRITICAL")


class TestExperimentImport(unittest.TestCase):

    test_data_module = "gumby.tests.data"
    test_class_module = test_data_module + ".foo.bar.my_module"

    test_data_folder = os.path.join(os.path.dirname(__file__), "data")
    test_class_folder = os.path.join(test_data_folder, "foo", "bar")

    def test_direct_import(self):
        module = ExperimentClient.direct_import("some.test.module.name",
                                                "my_module",
                                                TestExperimentImport.test_class_folder)

        self.assertIsNotNone(module)
        self.assertIn("some.test.module.name", sys.modules)

    def test_direct_import_non_existent(self):
        module = ExperimentClient.direct_import("some.other.test.module.name",
                                                "this_file_doesnt_exist",
                                                TestExperimentImport.test_class_folder)

        self.assertIsNone(module)
        self.assertNotIn("some.other.test.module.name", sys.modules)

    def test_duplicate_import(self):
        module1 = ExperimentClient.direct_import("some.test.module.name",
                                                 "my_module",
                                                 TestExperimentImport.test_class_folder)
        module2 = ExperimentClient.direct_import("some.test.module.name",
                                                 "my_module",
                                                 TestExperimentImport.test_class_folder)

        self.assertIsNotNone(module1)
        self.assertIsNotNone(module2)
        self.assertIn("some.test.module.name", sys.modules)
        self.assertEqual(module1, module2)

    def test_find_modules_no_class(self):
        init_folders, class_file, classes = ExperimentClient.find_modules_for(TestExperimentImport.test_class_module)

        foo_folder = os.path.join(TestExperimentImport.test_data_folder, "foo")
        foo_module = TestExperimentImport.test_data_module + ".foo"

        bar_folder = os.path.join(foo_folder, "bar")
        bar_module = foo_module + ".bar"

        self.assertGreaterEqual(len(init_folders), 2)
        self.assertEqual((foo_module, foo_folder), init_folders[-2])
        self.assertEqual((bar_module, bar_folder), init_folders[-1])
        self.assertNotIn((TestExperimentImport.test_data_module, TestExperimentImport.test_data_folder), init_folders)

        self.assertEqual((TestExperimentImport.test_class_module,
                          "my_module",
                          TestExperimentImport.test_class_folder), class_file)

        self.assertListEqual([], classes)

    def test_find_modules_with_class(self):
        init_folders, class_file, classes = ExperimentClient.find_modules_for(TestExperimentImport.test_class_module +
                                                                              ".MyModule")

        foo_folder = os.path.join(TestExperimentImport.test_data_folder, "foo")
        foo_module = TestExperimentImport.test_data_module + ".foo"

        bar_folder = os.path.join(foo_folder, "bar")
        bar_module = foo_module + ".bar"

        self.assertGreaterEqual(len(init_folders), 2)
        self.assertEqual((foo_module, foo_folder), init_folders[-2])
        self.assertEqual((bar_module, bar_folder), init_folders[-1])

        self.assertEqual((TestExperimentImport.test_class_module,
                          "my_module",
                          TestExperimentImport.test_class_folder), class_file)

        self.assertListEqual(["MyModule"], classes)

    def test_find_modules_sub_class(self):
        init_folders, class_file, classes = ExperimentClient.find_modules_for(TestExperimentImport.test_class_module +
                                                                              ".MyModule.MySubClass")

        foo_folder = os.path.join(TestExperimentImport.test_data_folder, "foo")
        foo_module = TestExperimentImport.test_data_module + ".foo"

        bar_folder = os.path.join(foo_folder, "bar")
        bar_module = foo_module + ".bar"

        self.assertGreaterEqual(len(init_folders), 2)
        self.assertEqual((foo_module, foo_folder), init_folders[-2])
        self.assertEqual((bar_module, bar_folder), init_folders[-1])

        self.assertEqual((TestExperimentImport.test_class_module,
                          "my_module",
                          TestExperimentImport.test_class_folder), class_file)

        self.assertListEqual(["MyModule", "MySubClass"], classes)

    def test_perform_class_import_module(self):
        module = ExperimentClient.perform_class_import(logging.getLogger(__name__),
                                                       0,
                                                       TestExperimentImport.test_class_module)

        # We loaded some module
        self.assertIsNotNone(module)
        self.assertIsInstance(module, types.ModuleType)
        # We loaded the requested module
        self.assertIn(TestExperimentImport.test_class_module, sys.modules)
        # We loaded all of the __init__'ed folders along the way
        self.assertIn(TestExperimentImport.test_data_module + ".foo", sys.modules)
        self.assertIn(TestExperimentImport.test_data_module + ".foo.bar", sys.modules)

    def test_perform_class_import_module_non_existent(self):
        module = ExperimentClient.perform_class_import(logging.getLogger(__name__),
                                                       0,
                                                       TestExperimentImport.test_data_module + "idontexist")

        self.assertIsNone(module)

    def test_perform_class_import_class(self):
        my_class = ExperimentClient.perform_class_import(logging.getLogger(__name__),
                                                         0,
                                                         TestExperimentImport.test_class_module + ".MyModule")

        # We loaded some class
        self.assertIsNotNone(my_class)
        self.assertEqual(my_class.__name__, "MyModule")
        # We loaded the requested module
        self.assertIn(TestExperimentImport.test_class_module, sys.modules)
        # We loaded all of the __init__'ed folders along the way
        self.assertIn(TestExperimentImport.test_data_module + ".foo", sys.modules)
        self.assertIn(TestExperimentImport.test_data_module + ".foo.bar", sys.modules)

    def test_perform_class_import_sub_class(self):
        my_class = ExperimentClient.perform_class_import(logging.getLogger(__name__),
                                                         0,
                                                         TestExperimentImport.test_class_module +
                                                         ".MyModule.MySubClass")

        # We loaded some class
        self.assertIsNotNone(my_class)
        self.assertEqual(my_class.__name__, "MySubClass")
        # We loaded the requested module
        self.assertIn(TestExperimentImport.test_class_module, sys.modules)
        # We loaded all of the __init__'ed folders along the way
        self.assertIn(TestExperimentImport.test_data_module + ".foo", sys.modules)
        self.assertIn(TestExperimentImport.test_data_module + ".foo.bar", sys.modules)
