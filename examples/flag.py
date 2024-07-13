from arcparse import arcparser, no_flag


@arcparser
class Args:
    # uses action="store_true"
    happy: bool

    # True, use --no-rich to set to False, uses action="store_false"
    rich: bool = no_flag()

    # None, use --married to set to True, use --no-married to set to False
    married: bool | None


if __name__ == "main":
    print(vars(Args.parse()))
