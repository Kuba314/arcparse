from arcparse import arcparser, subparsers


class Common:
    debug: bool


class FooArgs(Common):
    foo: bool


class BarArgs(Common):
    bar: bool


@arcparser
class Args:
    action: FooArgs | BarArgs = subparsers("foo", "bar")


if __name__ == "__main__":
    print(vars(Args.parse()))
