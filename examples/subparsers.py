from typing import Protocol

from arcparse import arcparser, positional, subparsers


class Action(Protocol):
    def run_action(self) -> None: ...


class HiAction(Action):
    name: str = positional()

    def run_action(self) -> None:
        print(f"Hi {self.name}")


class ByeAction(Action):
    name: str = positional()

    def run_action(self) -> None:
        print(f"Bye {self.name}")


@arcparser
class Args:
    action: Action = subparsers(hi=HiAction, bye=ByeAction)


if __name__ == "main":
    print(vars(Args.parse()))
