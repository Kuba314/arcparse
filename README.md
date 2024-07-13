# arcparse
Declare program arguments in a type-safe way.

This project builds on top of `argparse` by adding type-safety and allowing a more expressive argument parser definition.

## Example usage
```py
from arcparse import arcparser, flag
from pathlib import Path

@arcparser
class Args:
    path: Path
    recurse: bool = flag("-r")
    item_limit: int = 100
    output_path: Path | None

args = Args.parse()
print(f"Scanning {args.path}...")
...
```

For more examples see [Examples](examples/).

## Installation
```shell
# Using pip
$ pip install arcparse
```

## Features
- Positional, Option and Flag arguments
- Multiple values per argument
- Name overriding
- Type conversions
- Mutually exclusive groups
- Subparsers
- Parser inheritance

## Credits
This project was inspired by [swansonk14/typed-argument-parser](https://github.com/swansonk14/typed-argument-parser).

## Known issues

### Annotations
`from __future__ import annotations` makes all annotations strings at runtime. This library relies on class variable annotations's types being actual types. `inspect.get_annotations(obj, eval_str=True)` is used to evaluate string annotations to types in order to assign converters. If an argument is annotated with a non-builtin type which is defined outside of the argument-defining class body the type can't be found which results in `NameError`s. This is avoidable either by only using custom types which have been defined in the argument-defining class body (which is restrictive), or alternatively by not using the `annotations` import which should not be necessary from python 3.13 forward thanks to [PEP 649](https://peps.python.org/pep-0649/).
