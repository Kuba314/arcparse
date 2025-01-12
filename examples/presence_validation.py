from typing import Iterator

from arcparse import arcparser, positional
from arcparse.validations import Constraint, imply, require


@arcparser
class Args:
    """
    This parser implements a config subcommand similar to `git config`.

    Usage:
        `--list` displays configuration
        `--unset <key>` unsets the key
        `<key> <value>` sets the key to the value

    It would be impossible to create this parser using subparsers, since subparsers require a name to select
    the subparser used, while this example uses flags to select the action.

    This example could be partially implemented by just using a mutually exclusive group with `--list` and `--unset`
    but the presence of `key` wouldn't be required with `--unset` and similarly the presence of `value` wouldn't be
    required when neither `--list` nor `--unset` are present.
    """

    list: bool
    unset: bool
    key: str | None = positional()
    value: str | None = positional()

    @classmethod
    def __presence_validations__(cls) -> Iterator[Constraint]:
        """
        Generate argument presence constraints.

        The return value can be any iterable.
        """
        # --list is incompatible with --unset, key and value
        yield imply(cls.list, disallowed=[cls.unset, cls.key, cls.value])

        # --unset requires key, but is incompatible with value (incompatibility with --list is verified by
        # the previous constraint)
        yield imply(cls.unset, required=[cls.key], disallowed=[cls.value])

        # if none of the previous constraints matched (--list and --unset are not provided), require both key and value
        yield require(cls.key, cls.value)


if __name__ == "__main__":
    print(vars(Args.parse()))
