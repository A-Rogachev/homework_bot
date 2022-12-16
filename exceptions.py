class EnvironmentVariablesError(Exception):
    """
    Класс-исключение для обработки ошибок, 
    связанных с переменными окружения.
    """


class ApiResponseError(Exception):
    """
    Класс-исключение для некорректного ответа от API.
    """

class ApiCurrentDateError(Exception):
    """
    Класс-исключение для обработки ошибок,
    связанных с ключом "current_date" от API.
    """
