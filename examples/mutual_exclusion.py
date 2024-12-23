from arcparse import arcparser, flag, mx_group, option


@arcparser
class Args:
    # both arguments have to have a default
    value: int | None = option(mx_group=(group := mx_group()))
    flag: bool | None = flag(mx_group=group)


if __name__ == "__main__":
    print(vars(Args.parse()))
