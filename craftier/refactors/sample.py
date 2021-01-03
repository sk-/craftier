# pylint: disable=pointless-statement,no-self-use,using-constant-test

import craftier


class SquareTransformer(craftier.CraftierTransformer):
    def square_before(self, x):
        x * x

    def square_after(self, x):
        x ** 2


class IfTrueTransformer(craftier.CraftierTransformer):
    def if_true_before(self, x, y):
        x if True else y

    def if_true_after(self, x):
        x
