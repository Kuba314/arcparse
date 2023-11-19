# Arcparse
Declare program arguments declaratively and type-safely. Optionally set argument defaults dynamically (see [Dynamic argument defaults](#dynamic-argument-defaults)).

This project provides a wrapper around `argparse`. It adds type-safety and allows for more expressive argument parser definitions.

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
class Args(ArcParser):
    required: str
    optional: str | None
    default: str = "foo"
    default_with_help: str = option(default="bar", help="help message")
```

### Positional arguments
Positional arguments use `positional()`. Optional type-hints use `nargs="?"` in the background.
```py
class Args(ArcParser):
    required: str = positional()
    optional: str | None = positional()
```

### Flags
All arguments type-hinted as `bool` are flags, they use `action="store_true"` in the background. Use `no_flag()` to easily create a `--no-...` flag with `action="store_false"`. Flags as well as options can also define short forms for each argument. They can also disable the long form with `short_only=True`.
```py
class Args(ArcParser):
    sync: bool
    recurse: bool = no_flag(help="Do not recurse")

    debug: bool = flag("-d")  # both -d and --debug
    verbose: bool = flag("-v", short_only=True)  # only -v
```

### Multiple values per argument
By type-hinting the argument as `list[...]`, the argument will use `nargs="*"` in the background. Passing `append=True` to `option()` uses `action="append"` instead (this is available only for `option()`).
```py
class Args(ArcParser):
    option_nargs: list[str]
    positional_nargs: list[str] = positional()
```

### Type conversions
Automatic type conversions are supported. The type-hint is used in `type=...` in the background (unless it's `str`, which does no conversion). Using a `StrEnum` instance as a type-hint automatically populates `choices`. A custom type-converter can be used by passing `converter=...` to either `option()` or `positional()`. Come common utility converters are defined in [converters.py](arcparse/converters.py).

Custom converters may be used in combination with multiple values per argument. These converters are called `itemwise` and need to be wrapped in `itemwise()`. This wrapper is used automatically if an argument is typed as `list[...]` and no converter is set.
```py
from arcparse.converters import csv, itemwise

class Args(ArcParser):
    class Result(StrEnum):
        PASS = "pass"
        FAIL = "fail"

        @classmethod
        def from_int(cls, arg: str) -> Result:
            number = int(arg)
            return cls.PASS if number == 1 else cls.FAIL

    number: int
    result: Result
    custom: Result = option(converter=Result.from_int)
    ints: list[int] = option(converter=csv(int))
    results: list[Result] = option(converter=itemwise(Result.from_int))
```

### Name overriding
Type-hinting an option as `list[...]` uses `action="append"` in the background. Use this in combination with `name_override=...` to get rid of the `...s` suffixes.
```py
class Args(ArcParser):
    values: list[str] = option(name_override="value")
```

### Subparsers
Type-hinting an argument as a union of ArcParser subclasses creates subparsers in the background. Assigning from `subparsers()` gives them names as they will be entered from the command-line. Subparsers are required by default. Adding `None` to the union makes the subparsers optional.
```py
class FooArgs(ArcParser):
    arg1: str

class BarArgs(ArcParser):
    arg2: int = positional()

class Args(ArcParser):
    action: FooArgs | BarArgs = subparsers("foo", "bar")

class OptionalSubparsersArgs(ArcParser):
    action: FooArgs | BarArgs | None = subparsers("foo", "bar")
```

Once the arguments are parsed, the different subparsers can be triggered and distinguished like so:
```shell
python3 script.py foo --arg1 baz
python3 script.py bar --arg2 123
```
```py
args = Args.parse()
if isinstance(foo := args.action, FooArgs):
    print(f"foo {foo.arg1}")
elif isinstance(bar := args.action, BarArgs):
    print(f"bar {bar.arg2}")
```
Be aware that even though the `isinstance()` check passes, the instantiated subparser objects are never actual instances of their class because a dynamically created `dataclass` is used instead. The `isinstance()` relation is faked using a metaclass overriding `__instancecheck__()`.

## Dynamic argument defaults
The `parse()` classmethod supports an optional dictionary of defaults, which replace the statically defined defaults before parsing arguments. This might be useful for saving some arguments in a config file allowing the user to provide only the ones that are not present in the config.

## Credits
This project was inspired by [swansonk14/typed-argument-parser](https://github.com/swansonk14/typed-argument-parser).

## Known issues

### Annotations
`from __future__ import annotations` makes all annotations strings at runtime. This library relies on class variable annotations's types being actual types. `inspect.get_annotations(obj, eval_str=True)` is used to evaluate string annotations to types in order to assign converters. If an argument is annotated with a non-builtin type which is defined outside of the argument-defining class body the type can't be found which results in `NameError`s. This is avoidable either by only using custom types which have been defined in the argument-defining class body (which is restrictive), or alternatively by not using the `annotations` import which should not be necessary from python 3.13 forward thanks to [PEP 649](https://peps.python.org/pep-0649/).
