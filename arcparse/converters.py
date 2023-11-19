from collections.abc import Callable


class itemwise[T]:
    """Mark converter as itemwise

    This changes its return-type signature to wrap T in list. This is used in
    argument converter declaration. Argument converters returning T make the
    argument also return T. However if an itemwise conversion is desired on
    arguments accepting multiple values (nargs="*"), the return type should
    always be wrapped in a list.
    """
    def __init__(self, converter: Callable[[str], T]) -> None:
        self._converter = converter

    def __call__(self, string: str) -> list[T]:
        return self._converter(string)  # type: ignore


def csv[T](type_: type[T] = str, /) -> Callable[[str], list[T]]:
    def conv(arg: str) -> list[T]:
        return list(map(type_, arg.split(",")))

    return conv
