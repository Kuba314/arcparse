

class InvalidParser(Exception):
    pass


class InvalidArgument(InvalidParser):
    pass


class InvalidTypehint(InvalidArgument):
    pass


class MissingConverter(InvalidArgument):
    pass
