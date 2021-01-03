import pathlib
import time

import pyfakefs.fake_filesystem_unittest

from craftier import fs


class FsTest(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.files = [
            pathlib.Path("/tmp/file1"),
            pathlib.Path("/tmp/file2"),
            pathlib.Path("/tmp/dir/file1"),
        ]
        for f in self.files:
            self.fs.create_file(str(f), contents="")

    def test_no_modifed_files(self):
        last_update = max(f.stat().st_mtime for f in self.files)
        self.assertEqual(
            fs.get_modified_files(self.files, since=last_update), []
        )

    def test_modified_files(self):
        now = time.time()
        self.files[0].touch()
        self.files[2].write_text("foo")
        self.assertEqual(
            fs.get_modified_files(self.files, since=now),
            [self.files[0], self.files[2]],
        )
