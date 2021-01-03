import unittest

import pyfakefs

class TestCase(unittest.TestCase):
    fs: pyfakefs.FakeFilesystem
    def setUpPyfakefs(self) -> None: ...
