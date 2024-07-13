from arcparse import arcparser, option, positional


@arcparser
class Args:
    # uses nargs="*"
    favorite_things: list[str] = positional()

    # uses action="append", converts every argument to integer
    disliked_numbers: list[int] = option("-x", short_only=True, append=True)

    # uses nargs="+"
    # note that at_least_one=True will cause the option to be required, provide a default value if this is not intended
    liked_movies: list[str] = option(at_least_one=True)


if __name__ == "main":
    print(vars(Args.parse()))
