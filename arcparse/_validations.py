from abc import ABC, abstractmethod
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass

from arcparse.arguments import BaseArgument, BaseValueArgument, Flag


class ArgumentAccessor:
    def __init__(self, arguments: dict[str, BaseArgument]):
        self._arguments = arguments

    def __getattribute__(self, key: str) -> BaseArgument:
        arguments = super().__getattribute__("_arguments")
        if key not in arguments:
            raise Exception(f'Argument "{key}" doesn\'t exist')
        return arguments[key]


class Constraint(ABC):
    @abstractmethod
    def validate(self, arguments: dict[str, str]) -> bool: ...

    @staticmethod
    def is_provided(argument: BaseArgument, arguments: dict[str, str]) -> bool:
        if (provided_value := arguments.get(argument.name)) is None:
            return False

        if isinstance(argument, Flag):
            defined_default = argument.no_flag
        elif isinstance(argument, BaseValueArgument):
            defined_default = argument.default
        else:
            raise Exception(f"is_provided is not defined for {argument.__class__.__name__}")
        return provided_value != defined_default


@dataclass
class ImplyConstraint(Constraint):
    arg: BaseArgument
    required: Collection[BaseArgument]
    disallowed: Collection[BaseArgument]

    def validate(self, arguments: dict[str, str]) -> bool:
        if not self.is_provided(self.arg, arguments):
            return False

        for arg in self.required:
            if not self.is_provided(arg, arguments):
                raise Exception(f'Argument "{arg.display_name}" is required when "{self.arg.display_name}" is passed')

        for arg in self.disallowed:
            if self.is_provided(arg, arguments):
                raise Exception(f'Argument "{arg.display_name}" is incompatible with "{self.arg.display_name}"')
        return True


@dataclass
class RequireConstraint(Constraint):
    args: Collection[BaseArgument]

    def validate(self, arguments: dict[str, str]) -> bool:
        def and_join(names: Sequence[str]) -> str:
            if len(names) == 0:
                return ""
            elif len(names) == 1:
                return names[0]
            return f"{', '.join(names[:-1])} and {names[-1]}"

        not_provided = [arg for arg in self.args if not self.is_provided(arg, arguments)]
        if not_provided:
            provided_text = "none" if len(not_provided) == len(self.args) else "only some"
            raise Exception(
                f"Arguments {and_join([arg.display_name for arg in self.args])} are required together, but {provided_text} were provided"
            )
        return True


def validate_with(
    defined_arguments: dict[str, BaseArgument],
    validations_callable: Callable[[ArgumentAccessor], Iterable[Constraint]],
    provided_arguments: dict[str, str],
) -> None:
    for constraint in validations_callable(ArgumentAccessor(defined_arguments)):
        if not isinstance(constraint, Constraint):
            raise TypeError("Items returned from __validations__() have to be of type Constrant")

        matched = constraint.validate(provided_arguments)
        if matched:
            break
