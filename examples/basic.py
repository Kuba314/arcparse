from arcparse import arcparser, positional


# Arguments without explicitly assigned argument class are implicitly options (prefixed with `--`).
# A non-optional typehint results in `required=True` for options. Defaults can be set by directly
# assigning them. You can use `option()` to further customize the argument.


@arcparser
class Args:
    # required positional argument
    name: str = positional()

    # optional positional argument, will be None if not provided, uses nargs="?"
    last_name: str | None = positional()

    # required option argument
    age: int

    # optional option argument with a default
    n_siblings: int = 0


if __name__ == "main":
    print(vars(Args.parse()))
