class RequestExceptionError(Exception):
    """Ошибка запроса."""
    pass


class EmptyResponseError(Exception):
    """Недокументированный статус."""
    pass


class ResponceTypeError(TypeError):
    """Ошибка типа ответа сервера."""
    pass


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""
    pass
