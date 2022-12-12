import logging
import os
import time
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (ApiResponseError, EnvironmentVariablesError,
                        SendTelegramMessageError)

load_dotenv()

PRACTICUM_TOKEN: Optional[str] = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: Optional[str] = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: Dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS: Dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

API_RESPONSE_STRUCTURE = Dict[str, List[Dict[str, Any]]]

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler: logging.Handler = logging.StreamHandler()
logger.addHandler(handler)

formatter: logging.Formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s',
)
handler.setFormatter(formatter)


def check_tokens() -> None:
    """
    Проверяет доступность переменных окружения.
    """
    missing_variables: List[Tuple[str, str]] = list(
        filter(
            lambda x: x[0] is None, (
                (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
                (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'),
                (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
            )
        )
    )

    if missing_variables:
        message_err: str = ', '.join([var[1] for var in missing_variables])
        logger.critical(
            f'Отсутствуют следующие переменные окружения: {message_err}. '
            'Программа принудительно остановлена.'
        )
        raise EnvironmentVariablesError('Проверьте переменные окружения.')


def send_message(bot: telegram.Bot, message: str) -> None:
    """
    Отправляет сообщение в Telegram чат.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(
            f'Бот отправил сообщение "{message}"'
        )
    except Exception as telegram_error:
        logger.error(
            'Ошибка отправки сообщения в Telegram пользователя.',
            exc_info=True,
        )
        raise SendTelegramMessageError(
            f'!!! {telegram_error} !!!'
        )


def get_api_answer(timestamp: int) -> API_RESPONSE_STRUCTURE:
    """
    Делает запрос к эндпоинту API-сервиса.
    """
    try:
        api_response: Dict[str, Any] = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
    except requests.exceptions.RequestException:
        raise ApiResponseError(
            'При обработке запроса к API произошла ошибка.'
        )
    if api_response.status_code != HTTPStatus.OK:
        raise ApiResponseError(
            f'Эндпоинт {ENDPOINT} недоступен ('
            f'Код ответа: {api_response.status_code})'
        )
    return api_response.json()


def check_response(response: API_RESPONSE_STRUCTURE) -> None:
    """
    Проверяет ответ API на соответствие документации.
    """
    if not (isinstance(response, Dict)):
        raise TypeError('Структура данных ответа не соответствует ожиданиям.')
    if not response.get('homeworks'):
        raise KeyError('Ответ API не содержит данных о домашней работе.')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Структура данных о домашней работе '
            'не соответствует инструкции.'
        )


def parse_status(homework: Dict[str, Any]) -> str:
    """
    Извлекает из информации о дом. работе статус этой работы.
    """
    try:
        homework_name: str = homework['homework_name']
    except KeyError:
        raise ApiResponseError('В ответе API нет названия дом работы.')

    try:
        status_name: str = homework['status']
    except KeyError:
        raise ApiResponseError('В ответе API нет названия статуса')

    try:
        verdict: str = HOMEWORK_VERDICTS[status_name]
    except KeyError:
        raise ApiResponseError('Неизвестный статус дом. работы.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """
    Основная логика работы бота.
    """
    check_tokens()

    bot: telegram.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time())

    last_message: str = ''
    last_error_message: str = ''

    while True:
        try:
            api_response: API_RESPONSE_STRUCTURE = get_api_answer(timestamp)
            check_response(api_response)

            timestamp += RETRY_PERIOD
            all_user_homework = api_response['homeworks']

            if all_user_homework:
                message_from_api: str = parse_status(all_user_homework[0])

                if message_from_api != last_message:
                    last_message = message_from_api
                    send_message(bot, message_from_api)
                else:
                    logger.debug('Новые статусы домашней работы отсутствуют.')
            else:
                logger.debug('Список домашних работ пуст')

        except Exception as error:
            error_message: str = f'Сбой в работе программы: {error}'
            logger.error(error_message)
            if error_message != last_error_message:
                send_message(bot, error_message)
                last_error_message = error_message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
