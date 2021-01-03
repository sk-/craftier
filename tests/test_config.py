import pathlib
import textwrap

import pyfakefs.fake_filesystem_unittest

import craftier.config


class ConfigTest(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def test_load_from_path_invalid(self):
        config_path = pathlib.Path("/path/config.ini")
        self.fs.create_file(config_path, contents="{}")
        with self.assertRaises(craftier.config.InvalidConfigError):
            craftier.config.load(config_path)

    def test_load_from_path_no_section(self):
        config_path = pathlib.Path("/path/config.ini")
        self.fs.create_file(config_path, contents="")
        with self.assertRaises(craftier.config.InvalidConfigError):
            craftier.config.load(config_path)

    def test_load_from_path_empty_section(self):
        config_path = pathlib.Path("/path/config.ini")
        self.fs.create_file(config_path, contents="[craftier]")
        self.assertEqual(
            craftier.config.load(config_path),
            craftier.config.Config(path=config_path, packages=[], excluded=[]),
        )

    def test_load_from_path(self):
        config_path = pathlib.Path("/path/config.ini")
        config_data = textwrap.dedent(
            """
        [craftier]
        packages=a.refactors,
          b.refactors
        excluded=a.refactors.Foo,a.refactors.Bar,
          b.refactors.Baz
        """
        )
        self.fs.create_file(config_path, contents=config_data)
        self.assertEqual(
            craftier.config.load(config_path),
            craftier.config.Config(
                path=config_path,
                packages=["a.refactors", "b.refactors"],
                excluded=[
                    "a.refactors.Foo",
                    "a.refactors.Bar",
                    "b.refactors.Baz",
                ],
            ),
        )

    def test_load_from_default(self):
        self.assertEqual(
            craftier.config.load(None),
            craftier.config.Config(
                path=None,
            ),
        )

    def test_find_path_not_found(self):
        self.assertIsNone(craftier.config.find_path(pathlib.Path("/tmp/foo")))

    def test_find_path_found(self):
        self.fs.create_file("/tmp/foo/.craftier.ini")
        self.assertEqual(
            craftier.config.find_path(pathlib.Path("/tmp/foo/bar")),
            pathlib.Path("/tmp/foo/.craftier.ini"),
        )

    def test_find_path_stops_at_git(self):
        self.fs.create_file("/tmp/foo/.craftier.ini")
        self.fs.create_dir("/tmp/foo/bar/.git")
        self.assertIsNone(
            craftier.config.find_path(pathlib.Path("/tmp/foo/bar"))
        )

    def test_find_path_stops_at_mercurial(self):
        self.fs.create_file("/tmp/foo/.craftier.ini")
        self.fs.create_dir("/tmp/foo/bar/.hg")
        self.assertIsNone(
            craftier.config.find_path(pathlib.Path("/tmp/foo/bar"))
        )

    def test_find_path_stops_at_home(self):
        home = pathlib.Path.home()
        self.fs.create_file(str(home.parent / ".craftier.ini"))
        self.fs.create_dir(home)
        self.assertIsNone(craftier.config.find_path(home / "foo"))

    def test_find_path_stops_too_deep(self):
        self.fs.create_file("/tmp/foo/.craftier.ini")
        self.assertIsNone(
            craftier.config.find_path(
                pathlib.Path(
                    "/tmp/foo/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16/17/18/19/20/21/22/23/24/25"
                )
            )
        )

    def test_find_path_not_too_deep(self):
        self.fs.create_file("/tmp/foo/.craftier.ini")
        self.assertEqual(
            craftier.config.find_path(
                pathlib.Path(
                    "/tmp/foo/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16/17/18/19/20/21/22/23/24"
                )
            ),
            pathlib.Path("/tmp/foo/.craftier.ini"),
        )
