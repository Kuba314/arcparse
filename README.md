# Arcparse
Declare program arguments declaratively and type-safely. Optionally set argument defaults dynamically (see [Dynamic argument defaults](#dynamic-argument-defaults))

Disclaimer: This library is young and probably highly unstable. Use at your own risk. Pull requests are welcome.

## Example usage
```py
from arcparse import ArcParser, positional


class Args(ArcParser):
    name: str = positional()
    age: int = positional()
    hobbies: list[str] = positional()
    happy: bool


args = Args.parse()
print(f"Hi, my name is {args.name}!")
```

For a complete overview of features see [Features](#features).

## Installation
```shell
# Using pip
$ pip install arcparse

# locally using poetry
$ poetry install
```

## Features

### Required and optional arguments
Arguments without explicitly assigned argument class are implicitly options (prefixed with `--`). A non-optional typehint results in `required=True` for options. Defaults can be set by directly assigning them. You can use `option()` to further customize the argument.
```py
class Required(ArcParser):
    required: str
    optional: str | None
    default: str = "foo"
    default_with_help: str = option(default="bar", help="help message")
```

### Positional arguments
Positional arguments use `positional()`. Type-hinting the argument as `list[...]` uses `nargs="*"` in the background for positional arguments.
```py
class Positional(ArcParser):
    single: str = positional()
    multiple: list[str] = positional()
```

### Flags
All arguments type-hinted as `bool` are flags, they use `action="store_true"` in the background. Use `no_flag()` to easily create a `--no-...` with `action="store_false"`. Flags as well as options can also define short forms for each argument. They can also disable the long form with `short_only=True`.
```py
class FlagArgs(ArcParser):
    sync: bool
    recurse: bool = no_flag(help="Do not recurse")

    debug: bool = flag("-d")  # both -d and --debug
    verbose: bool = flag("-v", short_only=True)  # only -v
```

### Type conversions
Automatic type conversions are supported. The type-hint is used in `type=...` in the background (unless it's `str`, which does no conversion). Using a `StrEnum` instance as a type-hint automatically populates `choices`. A custom type-converter can be used by passing `converter=...` to either `option` or `positional`.
```py
class TypeArgs(ArcParser):
    class Result(StrEnum):
        PASS = "pass"
        FAIL = "fail"

        @classmethod
        def from_int(cls, arg: str) -> Self:
            number = int(arg)
            return cls.PASS if number == 1 else cls.FAIL

    number: int
    result: Result
    custom: Result = option(converter=Result.from_int)
```

### Name overriding
Type-hinting an option as `list[...]` uses `action="append"` in the background. Use this in combination with `name_override=...` to get rid of the `...s` suffixes.
```py
class NameOverrideArgs(ArcParser):
    values: list[str] = option(name_override="value")
```

## Dynamic argument defaults
The `parse()` classmethod supports an optional dictionary of defaults, which replace the statically defined defaults before parsing arguments. This might be useful for saving some arguments in a config file allowing the user to provide only the ones that are not present in the config.

## Credits
This project was inspired by [swansonk14/typed-argument-parser](https://github.com/swansonk14/typed-argument-parser).
