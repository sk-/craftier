from typing import Union

import libcst.matchers

Matcher = Union[
    libcst.matchers.BaseMatcherNode, libcst.matchers.DoNotCareSentinel
]
