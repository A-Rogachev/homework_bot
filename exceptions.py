class EnvironmentVariablesError(Exception):
    """
    Класс-исключение для обработки ошибок, 
    связанных с переменными окружения.
    """


class ApiResponseError(Exception):
    """
    Класс-исключение для некорректного ответа от API.
    """

class SendTelegramMessageError(Exception):
    """
    Класс-исключение для работы с Телеграм-ботом.
    """
