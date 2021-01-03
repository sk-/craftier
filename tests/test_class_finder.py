import unittest

from craftier import class_finder


class _Needle:
    pass


class _ShinyNeedle(_Needle):
    pass


class _RustyNeedle(_Needle):
    pass


class ClassFinderTest(unittest.TestCase):
    def test_package_name(self):
        self.assertEqual(
            class_finder.from_qualified_names(_Needle, ["tests"]),
            [_Needle, _RustyNeedle, _ShinyNeedle],
        )

    def test_module_name(self):
        self.assertEqual(
            class_finder.from_qualified_names(
                _Needle, ["tests.test_class_finder"]
            ),
            [_Needle, _RustyNeedle, _ShinyNeedle],
        )

    def test_multiple_without_duplicates(self):
        self.assertEqual(
            class_finder.from_qualified_names(
                _Needle, ["tests", "tests.test_class_finder"]
            ),
            [_Needle, _RustyNeedle, _ShinyNeedle],
        )

    def test_invalid_name(self):
        with self.assertRaises(class_finder.InvalidName):
            class_finder.from_qualified_names(_Needle, ["unknown.package"])

    def test_no_matches(self):
        self.assertEqual(
            class_finder.from_qualified_names(int, ["tests.test_class_finder"]),
            [],
        )
