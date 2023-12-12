# Arcparse
Declare program arguments declaratively and type-safely.

This project provides a wrapper around `argparse`. It adds type-safety and allows for more expressive argument parser definitions.

Disclaimer: This library is young and probably highly unstable. Use at your own risk. Pull requests are welcome.

## Example usage
```py
from arcparse import arcparser, positional

@arcparser
class Args:
    name: str = positional()
    age: int = positional()
    hobbies: list[str] = positional()
    happy: bool


args = Args.parse("Thomas 25 news coffee running --happy".split())
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
@arcparser
class Args:
    required: str
    optional: str | None
    default: str = "foo"
    default_with_help: str = option(default="bar", help="help message")
```

### Positional arguments
Positional arguments use `positional()`. Optional type-hints use `nargs="?"` in the background.
```py
@arcparser
class Args:
    required: str = positional()
    optional: str | None = positional()
```

### Flags
All arguments type-hinted as `bool` are flags, they use `action="store_true"` in the background. Use `no_flag()` to easily create a `--no-...` flag with `action="store_false"`. Flags as well as options can also define short forms for each argument. They can also disable the long form with `short_only=True`.
```py
@arcparser
class Args:
    sync: bool
    recurse: bool = no_flag(help="Do not recurse")

    debug: bool = flag("-d")  # both -d and --debug
    verbose: bool = flag("-v", short_only=True)  # only -v
```

### Multiple values per argument
By type-hinting the argument as `list[...]`, the argument will use `nargs="*"` in the background. Passing `at_least_one=True` uses `nargs="+"` instead. Passing `append=True` to `option()` uses `action="append"` instead (this is available only for `option()` and incompatible with `at_least_one`).
```py
@arcparser
class Args:
    option_nargs: list[str]
    positional_nargs: list[str] = positional()
    append_option: list[str] = option(append=True)
    nargs_plus_option: list[str] = option(at_least_one=True)
    nargs_plus_positional: list[str] = positional(at_least_one=True)
```

Note that `option(at_least_one=True)` will cause the option to be required. If this is not intended, provide a default value.

### Name overriding
Passing `name_override=...` will cause the provided string to be used instead of the variable name for the argument name. The string will undergo a replacement of `_` with `-` and will contain a `--` prefix if used in `option()`.

This is useful in combination with accepting multiple values with `append=True`, because the user will use `--value foo --value bar`, while the code will use `args.values`.
```py
@arcparser
class Args:
    values: list[str] = option(name_override="value", append=True)
```

### Type conversions
Automatic type conversions are supported. The type-hint is used in `type=...` in the background (unless it's `str`, which does no conversion). Using a `StrEnum` subclass as a type-hint automatically populates `choices`. Using a `re.Pattern` typehint automatically uses `re.compile` as a converter. A custom type-converter can be used by passing `converter=...` to either `option()` or `positional()`. Come common utility converters are defined in [converters.py](arcparse/converters.py).

Custom converters may be used in combination with multiple values per argument. These converters are called `itemwise` and need to be wrapped in `itemwise()`. This wrapper is used automatically if an argument is typed as `list[...]` and no converter is set.
```py
from arcparse.converters import sv, csv, sv_dict, itemwise
from enum import StrEnum
from re import Pattern

@arcparser
class Args:
    class Result(StrEnum):
        PASS = "pass"
        FAIL = "fail"

        @classmethod
        def from_int(cls, arg: str) -> "Result":
            number = int(arg)
            return cls.PASS if number == 1 else cls.FAIL

    number: int
    result: Result
    pattern: Pattern
    custom: Result = option(converter=Result.from_int)
    ints: list[int] = option(converter=csv(int))
    ip_parts: list[int] = option(converter=sv(".", int), name_override="ip")
    int_overrides: dict[str, int] = option(converter=sv_dict(",", "=", value_type=int))  # accepts x=1,y=2
    results: list[Result] = option(converter=itemwise(Result.from_int))
```

### Mutually exclusive groups
Use `mx_group` to group multiple arguments together in a mutually exclusive group. Each argument has to have a default defined either implicitly through the type (being `bool` or a union with `None`) or explicitly with `default`.
```py
@arcparser
class Args:
    group = MxGroup()  # alternatively use `(group := MxGroup())` on the next line
    flag: bool = flag(mx_group=group)
    option: str | None = option(mx_group=group)
```

### Subparsers
Type-hinting an argument as a union of ArcParser subclasses creates subparsers in the background. Assigning from `subparsers()` gives them names as they will be entered from the command-line. Subparsers are required by default. Adding `None` to the union makes the subparsers optional.
```py
class FooArgs:
    arg1: str

class BarArgs:
    arg2: int = positional()

@arcparser
class Args:
    action: FooArgs | BarArgs = subparsers("foo", "bar")

@arcparser
class OptionalSubparsersArgs:
    action: FooArgs | BarArgs | None = subparsers("foo", "bar")
```

Once the arguments are parsed, the different subparsers can be triggered and distinguished like so:
```shell
python3 script.py foo --arg1 baz
python3 script.py bar --arg2 123
```
```py
args = Args.parse("foo --arg1 baz".split())
if isinstance(foo := args.action, FooArgs):
    print(f"foo {foo.arg1}")
elif isinstance(bar := args.action, BarArgs):
    print(f"bar {bar.arg2}")
```
Be aware that even though the `isinstance()` check passes, the instantiated subparser objects are never actual instances of their class because a dynamically created `dataclass` is used instead. The `isinstance()` relation is faked using a metaclass overriding `__instancecheck__()`.

## Credits
This project was inspired by [swansonk14/typed-argument-parser](https://github.com/swansonk14/typed-argument-parser).

## Known issues

### Annotations
`from __future__ import annotations` makes all annotations strings at runtime. This library relies on class variable annotations's types being actual types. `inspect.get_annotations(obj, eval_str=True)` is used to evaluate string annotations to types in order to assign converters. If an argument is annotated with a non-builtin type which is defined outside of the argument-defining class body the type can't be found which results in `NameError`s. This is avoidable either by only using custom types which have been defined in the argument-defining class body (which is restrictive), or alternatively by not using the `annotations` import which should not be necessary from python 3.13 forward thanks to [PEP 649](https://peps.python.org/pep-0649/).
