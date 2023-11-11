class RequestExceptionError(Exception):
    """Ошибка запроса."""
    pass


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""
    pass


class EmptyResponseError(Exception):
    """Недокументированный статус."""
    pass
