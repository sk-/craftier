import unittest

from craftier import performance


# pylint: disable=protected-access
class PerformanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            performance.disable()
        except performance.PerformanceError:
            pass

    def tearDown(self):
        try:
            performance.disable()
        except performance.PerformanceError:
            pass

    def test_enable(self) -> None:
        performance.enable()
        self.assertIsNotNone(performance._config.file)

    def test_enable_twice(self) -> None:
        performance.enable()
        with self.assertRaises(performance.PerformanceError):
            performance.enable()

    def test_read_not_enabled(self) -> None:
        self.assertEqual(performance.read(), [])

    def test_read_empty(self) -> None:
        performance.enable()
        self.assertEqual(performance.read(), [])

    def test_write_read(self) -> None:
        performance.enable()
        performance.write({"foo": 1})
        performance.write({"bar": 2})
        self.assertEqual(performance.read(), [{"foo": 1}, {"bar": 2}])

    def test_write_read_write_read(self) -> None:
        performance.enable()
        performance.write({"foo": 1})
        self.assertEqual(performance.read(), [{"foo": 1}])
        performance.write({"bar": 2})
        self.assertEqual(performance.read(), [{"foo": 1}, {"bar": 2}])

    def test_disable(self) -> None:
        performance.enable()
        performance.disable()
        self.assertIsNone(performance._config.file)

    def test_disable_not_enabled(self) -> None:
        with self.assertRaises(performance.PerformanceError):
            performance.disable()
