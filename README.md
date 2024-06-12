# arcparse
Declare program arguments type-safely.

This project builds on top of `argparse` by adding type-safety and allowing a more expressive argument parser definition.

Disclaimer: This library is young and relatively unstable. Issues are open and pull requests are welcome!

## Example usage
```py
from arcparse import arcparser, positional

@arcparser
class Args:
    name: str = positional()
    age: int
    happy: bool


args = Args.parse("--age 25 --happy Thomas".split())
print(f"Hi, my name is {args.name}!")
```

For a complete overview of features see [Features](#features).

## Installation
```shell
# Using pip
$ pip install arcparse
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
All arguments type-hinted as `bool` are flags, they use `action="store_true"` in the background. Flags (as well as options) can also define short forms for each argument. They can also disable the long form with `short_only=True`.

Use `no_flag()` to easily create a `--no-...` flag with `action="store_false"`.

Use `tri_flag()` (or type-hint argument as `bool | None`) to create a "true" flag and a "false" flag (e.g. `--clone` and `--no-clone`). Passing `--clone` will store `True`, passing `--no-clone` will store `False` and not passing anything will store `None`. Passing both is an error ensured by an implicit mutually exclusive group.
```py
@arcparser
class Args:
    sync: bool
    recurse: bool = no_flag(help="Do not recurse")
    clone: bool | None

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
Automatic type conversions are supported. The type-hint type is used to convert the string argument to the desired type. This is NOT done using argparse's `type=...` because it was causing issues for `dict_option()` and `dict_positional()`. Using a `StrEnum` subclass as a type-hint automatically populates `choices`, using `Literal` also populates choices but does not set converter unlike `StrEnum`. Using a `re.Pattern` typehint automatically uses `re.compile` as a converter. A custom type-converter can be used by passing `converter=...` to either `option()` or `positional()`. Come common utility converters are defined in [converters.py](arcparse/converters.py).

Custom converters may be used in combination with multiple values per argument. These converters are called `itemwise` and need to be wrapped in `itemwise()`. This wrapper is used automatically if an argument is typed as `list[...]` and no converter is set.
```py
from arcparse.converters import sv, csv, sv_dict, itemwise
from enum import StrEnum
from re import Pattern
from typing import Literal

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
    literal: Literal["yes", "no"]
    pattern: Pattern
    custom: Result = option(converter=Result.from_int)
    ints: list[int] = option(converter=csv(int))
    ip_parts: list[int] = option(converter=sv(".", int), name_override="ip")
    int_overrides: dict[str, int] = option(converter=sv_dict(",", "=", value_type=int))  # accepts x=1,y=2
    results: list[Result] = option(converter=itemwise(Result.from_int))
```

### dict helpers
Sometimes creating an argument able to choose a value from a dict by its key is desired. `dict_option()` and `dict_positional()` do exactly that. In the following example passing `--foo yes` will result in `.foo` being `True`.
```py
from arcparse import dict_option

values = {
    "yes": True,
    "no": False,
}

@arcparser
class Args:
    foo: bool = dict_option(values)
```

### Mutually exclusive groups
Use `mx_group` to group multiple arguments together in a mutually exclusive group. Each argument has to have a default defined either implicitly through the type (being `bool` or a union with `None`) or explicitly with `default`.
```py
@arcparser
class Args:
    group = mx_group()  # alternatively use `mx_group=(group := mx_group())` on the next line
    flag: bool = flag(mx_group=group)
    option: str | None = option(mx_group=group)
```

### Subparsers
Use the `subparsers()` function to create subparsers. The function accepts either subparser names as `*args` or name-type pairs of `**kwargs`. The former option relies on the typehint to be a union of types, while the latter option ignores the typehint altogether, but it has to be type-compatible with the provided types.

The subparsers positional is required by default. To make it optional, add `None` to the union in the typehint.

When nesting subparsers, avoid giving your subparsers the same name (e.g. `action`). `argparse` doesn't seem able to differentiate between different subparser levels with the same name. This applies to arguments as well -- arguments deeper in the subparser tree will overwrite arguments with the same name being closer to the root.
```py
class FooArgs:
    arg1: str

class BarArgs:
    arg2: int = positional()

@arcparser
class Args:
    action: FooArgs | BarArgs = subparsers("foo", "bar")
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

Each subparser class can define methods which (if defined for all subparsers) will become available on the result. The previous `isinstance()` if statements behaviour could be moved to a method of each subparser and the method could be simply called by calling `args.action.my_method()`.

The following code utilizes the previously mentioned `**kwargs` method of initializing subparsers.
```py
from typing import Protocol

class Action(Protocol):
    def my_method(self) -> None:
        ...

class FooArgs:
    arg1: str

    def my_method(self) -> None:
        print(f"foo {self.arg1}")

class BarArgs:
    arg2: int = positional()

    def my_method(self) -> None:
        print(f"bar {self.arg2}")

@arcparser
class Args:
    action: Action = subparsers(
        foo=FooArgs,
        bar=BarArgs,
    )

args = Args.parse("foo --arg1 baz".split())
args.action.my_method()
```

### Parser inheritance
Parsers can inherit arguments from other parsers. This is useful if there are common arguments among multiple subparsers. Note that current implementation disallows inheriting directly from classes already wrapped by `@arcparser`, inherit from `ClassAlreadySubparsered.shape` instead (if `Common` was wrapped in `@arcparser`, inherit from `Common.shape`).

```py
class Common:
    debug: bool

class FooArgs(Common):
    foo: bool

class BarArgs(Common):
    bar: bool

@arcparser
class Args:
    action: FooArgs | BarArgs = subparsers("foo", "bar")

args = Args.parse("foo --debug".split())
```

## Credits
This project was inspired by [swansonk14/typed-argument-parser](https://github.com/swansonk14/typed-argument-parser).

## Known issues

### Annotations
`from __future__ import annotations` makes all annotations strings at runtime. This library relies on class variable annotations's types being actual types. `inspect.get_annotations(obj, eval_str=True)` is used to evaluate string annotations to types in order to assign converters. If an argument is annotated with a non-builtin type which is defined outside of the argument-defining class body the type can't be found which results in `NameError`s. This is avoidable either by only using custom types which have been defined in the argument-defining class body (which is restrictive), or alternatively by not using the `annotations` import which should not be necessary from python 3.13 forward thanks to [PEP 649](https://peps.python.org/pep-0649/).
