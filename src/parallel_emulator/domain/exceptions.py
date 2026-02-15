class DomainException(Exception):
    """Базовий виняток домену"""


class InvalidBlockException(DomainException):
    """Некоректний блок"""


class DuplicateThreadException(DomainException):
    """Потік з таким ID вже існує"""