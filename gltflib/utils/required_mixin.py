from dataclasses import dataclass


# noinspection PyPep8Naming
class _MISSING_TYPE:
    """
    Helper class for required dataclass fields with no default values. This type should not be used directly. Rather,
    the MISSING value should be used to initialize a dataclass field. See documentation for RequiredMixin for more
    information.

    Note the __iter__, __next, and other functions defined on this class are mainly for interoperability with the
    dataclasses_json library, which will attempt to iterate and perform item assignments on objects when
    encoding/decoding.
    """

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration

    def __getitem__(self, item):
        return None

    def __setitem__(self, key, value):
        pass


MISSING = _MISSING_TYPE()


@dataclass
class RequiredMixin:
    """
    Helper class for dataclasses that have required fields with no default values. This mixin allows required fields
    to be defined in any order, regardless of whether they have a default value or not, and is especially useful in
    scenarios where a base dataclass defines defaults for some of its fields, and a derived class has a required field
    without a default.

    For example, suppose you have a base dataclass with a field that has a default value:

        from dataclasses import dataclass

        @dataclass
        class MyBaseClass:
            field1: str = None

    And you want to have an inherited dataclass that has a field without a default value:

        from dataclasses import dataclass

        @dataclass
        class MyDerivedClass(MyBaseClass):
            field2: str

    As written, this will result in an error:

        TypeError: non-default argument 'field2' follows default argument

    This is a limitation of the dataclass library: it prevents you from being able to use attributes with defaults in a
    base class and then use attributes without a default (positional attributes) in a subclass.

    The RequiredMixin helper is a workaround for this limitation. To use it:

        (1) The derived class must inherit from RequiredMixin
        (2) Any fields for which you do not want to provide a default value should be assigned the special value
            MISSING (also defined in this file). This special value will cause an error with a clear message to be
            thrown when the dataclass is initialized without another value being set.

    Example usage:

        from dataclasses import dataclass
        from .required_mixin import RequiredMixin, MISSING

        @dataclass
        class MyBaseClass:
            field1: str = None

        @dataclass
        class MyDerivedClass(MyBaseClass, RequiredMixin):
            field2: str = MISSING

    More information available here:
    https://stackoverflow.com/questions/51575931/class-inheritance-in-python-3-7-dataclasses
    """

    def __post_init__(self):
        for key, value in self.__dict__.items():
            if isinstance(value, _MISSING_TYPE):
                raise TypeError(f"{self.__class__.__name__} __init__ missing 1 required argument: '{key}'")
