import pathlib
import unittest

from click import testing

from craftier import cli

INPUT_FILE_CONTENTS = """
foo(x * x)
foo(bar((baz+1) * (baz + 1)))
bla if True else None
"""

REFACTORED_FILE_CONTENTS = """
foo(x ** 2)
foo(bar((baz+1) ** 2))
bla
"""


class TestCli(unittest.TestCase):
    def setUp(self):
        self.runner = testing.CliRunner()

    def testNoCommand(self) -> None:
        result = self.runner.invoke(cli.app, [], catch_exceptions=False)
        self.assertIn("Your personal Python code reviewer", result.output)
        self.assertIn("pre-α", result.output)
        self.assertEqual(result.exit_code, 0)

    def testRefactorNoFiles(self) -> None:
        result = self.runner.invoke(
            cli.app, ["refactor"], catch_exceptions=False
        )
        self.assertIn("No path provided. Nothing to do 💤", result.output)
        self.assertEqual(result.exit_code, 0)

    def testRefactorInvalidConfig(self) -> None:
        with self.runner.isolated_filesystem():
            pathlib.Path("craftier.ini").write_text("")
            pathlib.Path("refactored.py").write_text(REFACTORED_FILE_CONTENTS)
            result = self.runner.invoke(
                cli.app,
                ["refactor", "--config", "craftier.ini", "refactored.py"],
                catch_exceptions=False,
            )
            self.assertIn("missing", result.output)
            self.assertEqual(result.exit_code, 1)

    def testRefactorNoTransformersConfig(self) -> None:
        with self.runner.isolated_filesystem():
            pathlib.Path("craftier.ini").write_text("[craftier]\npackages=")
            pathlib.Path("refactored.py").write_text(REFACTORED_FILE_CONTENTS)
            result = self.runner.invoke(
                cli.app,
                ["refactor", "--config", "craftier.ini", "refactored.py"],
                catch_exceptions=False,
            )
            self.assertIn("No tranformers were specified", result.output)
            self.assertEqual(result.exit_code, 1)

    def testRefactorInvalidPackageConfig(self) -> None:
        with self.runner.isolated_filesystem():
            pathlib.Path("craftier.ini").write_text(
                "[craftier]\npackages=invalid.package.name"
            )
            pathlib.Path("refactored.py").write_text(REFACTORED_FILE_CONTENTS)
            result = self.runner.invoke(
                cli.app,
                ["refactor", "--config", "craftier.ini", "refactored.py"],
                catch_exceptions=False,
            )
            self.assertIn(
                "Package invalid.package.name is not valid. Are you missing any dependencies?",
                result.output,
            )
            self.assertEqual(result.exit_code, 1)

    def testRefactorFiles(self) -> None:
        with self.runner.isolated_filesystem():
            pathlib.Path("input.py").write_text(INPUT_FILE_CONTENTS)
            pathlib.Path("refactored.py").write_text(REFACTORED_FILE_CONTENTS)
            result = self.runner.invoke(
                cli.app,
                ["refactor", "refactored.py", "input.py"],
                catch_exceptions=False,
            )
            self.assertIn("refactored input.py", result.output)
            self.assertIn("All done!", result.output)
            self.assertIn(
                "1 file refactored, 1 file left unchanged", result.output
            )
            self.assertEqual(result.exit_code, 0)

            self.assertEqual(
                pathlib.Path("input.py").read_text(), REFACTORED_FILE_CONTENTS
            )

    def testRefactorFilesDebugMode(self) -> None:
        with self.runner.isolated_filesystem():
            pathlib.Path("input.py").write_text(INPUT_FILE_CONTENTS)
            pathlib.Path("refactored.py").write_text(REFACTORED_FILE_CONTENTS)
            result = self.runner.invoke(
                cli.app,
                ["refactor", "--debug", "refactored.py", "input.py"],
                catch_exceptions=False,
            )
            self.assertIn("Config path: None", result.output)
            self.assertIn("Checking", result.output)
            self.assertIn("Overall\tcount=", result.output)

            self.assertEqual(result.exit_code, 0)
