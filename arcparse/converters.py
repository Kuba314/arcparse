from collections.abc import Callable


def csv[T](type_: type[T] = str, /) -> Callable[[str], list[T]]:
    def conv(arg: str) -> list[T]:
        return list(map(type_, arg.split(",")))

    return conv
