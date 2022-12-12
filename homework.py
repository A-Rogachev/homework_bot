
import logging
import os
import time
from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Tuple

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (ApiResponseError, EnvironmentVariablesError,
                        SendTelegramMessageError)

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler: logging.Handler = logging.StreamHandler()
logger.addHandler(handler)

formatter: logging.Formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s',
)
handler.setFormatter(formatter)

load_dotenv()

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: Dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS: Dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> None:
    """
    Проверяет доступность переменных окружения.
    """
    missing_variables: List[Tuple[str]] = list(
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
        logging.critical(
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
    except Exception:
        raise SendTelegramMessageError(
            'Ошибка отправки сообщения в Telegram пользователя.'
        )


def get_api_answer(timestamp: int) -> Dict[str, Any]:
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


def check_response(response: Dict[str, Any]) -> Dict[str, str]:
    """
    Проверяет ответ API на соответствие документации.
    """
    if not (isinstance(response, Dict)):
        raise TypeError('Структура данных ответа не соответствует ожиданиям.')
    if not 'homeworks' in response:
        raise KeyError('Ответ API не содержит данных о домашней работе.')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Структура данных о домашней работе '
            'не соответствует инструкции.'
        )

    if not response.get('homeworks'):
        raise IndexError(
            f'На дату {datetime.fromtimestamp(response["current_date"])} '
            'нет информации о домашней работе пользователя.'
        )

    return response.get('homeworks')[0]


def parse_status(homework: Dict[str, Any]) -> str:
    """
    Извлекает из информации о дом. работе статус этой работы.
    """
    if 'homework_name' not in homework:
        raise KeyError('В ответе API нет названия домашней работы')
    else:
        homework_name = homework.get('homework_name')

    if 'status' not in homework:
        raise KeyError('В ответе API нет названия статуса')
    else:
        status_name = homework.get('status')

    if status_name in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS.get(status_name)
    else:
        raise KeyError('Такого статуса нет в словаре')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """
    Основная логика работы бота.
    """
    check_tokens()

    bot: telegram.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time()) - RETRY_PERIOD
    # timestamp: int = 0

    while True:
        try:
            api_response: Dict[str, Any] = get_api_answer(timestamp)
            checked_response: Dict[str, str] = check_response(api_response)

            message_from_api: str = parse_status(checked_response)
            send_message(bot, message_from_api)
            
        except Exception as error:
            message: str = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
