from enum import Enum


class OperationalModule(str, Enum):
    CAFE = "CAFE"
    PAPELERIA = "PAPELERIA"


def operational_module_value(
    value: OperationalModule | str,
) -> str:
    if isinstance(value, OperationalModule):
        return value.value

    return OperationalModule(
        str(value).strip().upper()
    ).value
