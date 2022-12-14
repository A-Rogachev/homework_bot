import logging
import os
import time
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiResponseError, EnvironmentVariablesError

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
HOMEWORKS_STRUCTURE = Optional[List[Dict[str, Any]]]

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler: logging.Handler = logging.StreamHandler()
logger.addHandler(handler)

formatter: logging.Formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s',
)
handler.setFormatter(formatter)


def check_tokens() -> None:
    """Проверяет доступность переменных окружения."""
    token_name_value_list: List[Tuple[str, Optional[str]]] = [
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
    ]

    missing_tokens: List[str] = [
        token_name for token_name, value in token_name_value_list if not value
    ]

    if missing_tokens:
        message_err: str = ', '.join([token for token in missing_tokens])
        logger.critical(
            f'Отсутствуют следующие переменные окружения: {message_err}. '
            'Программа принудительно остановлена.'
        )
        raise EnvironmentVariablesError('Проверьте переменные окружения.')


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as tg_error:
        print('я здесь')
        logger.error(
            'Ошибка отправки сообщения в Telegram пользователя: '
            f'({tg_error}).',
            exc_info=True,
        )
    else:
        logger.debug(
            f'Бот отправил сообщение "{message}"'
        )


def get_api_answer(timestamp: int) -> API_RESPONSE_STRUCTURE:
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        api_response: Dict[str, Any] = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )

        if api_response.status_code != HTTPStatus.OK:
            raise ApiResponseError(
                f'Эндпоинт {ENDPOINT} недоступен ('
                f'Код ответа: {api_response.status_code})'
            )
        api_response_content: API_RESPONSE_STRUCTURE = api_response.json()

    except requests.exceptions.JSONDecodeError:
        raise ApiResponseError(
            'Ошибка декодирования данных ответа формата json.'
        )
    except requests.exceptions.RequestException as request_error:
        raise ApiResponseError(
            'При обработке запроса к API произошла ошибка '
            f'({request_error}).'
        )
    else:
        return api_response_content


def check_response(response: API_RESPONSE_STRUCTURE) -> HOMEWORKS_STRUCTURE:
    """Проверяет ответ API на соответствие документации."""
    if not (isinstance(response, dict)):
        raise TypeError(
            f'Структура ответа API ({type(response)}), '
            'не соответствует ожидаемому (словарь).'
        )
    if not response.get('homeworks'):
        raise KeyError('Ответ API не содержит данных о домашней работе.')
    if not response.get('current_date'):
        raise KeyError('Ответ API не содержит данных о текущей дате.')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Структура данных о домашней работе '
            'не соответствует инструкции.'
        )
    return response.get('homeworks')


def parse_status(homework: Dict[str, Any]) -> str:
    """Извлекает из информации о дом. работе статус этой работы."""
    if 'homework_name' in homework:
        homework_name: str = homework['homework_name']
    else:
        raise KeyError('В ответе API нет названия домашней работы.')

    if 'status' in homework:
        status_name: str = homework['status']
    else:
        raise KeyError('В ответе API нет названия статуса')

    if status_name in HOMEWORK_VERDICTS:
        verdict: str = HOMEWORK_VERDICTS[status_name]
    else:
        raise KeyError('Неизвестный статус дом. работы.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    check_tokens()

    bot: telegram.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time())
    last_message: str = ''

    while True:
        try:
            api_response: API_RESPONSE_STRUCTURE = get_api_answer(timestamp)
            all_user_homework: HOMEWORKS_STRUCTURE = check_response(
                api_response
            )

            if all_user_homework:
                message_from_api: str = parse_status(all_user_homework[0])

                if message_from_api != last_message:
                    last_message: str = message_from_api
                    send_message(bot, message_from_api)

            timestamp: int = api_response.get('current_date')

        except Exception as error:
            error_message: str = f'Сбой в работе программы: {error}'
            logger.error(error_message)
            if error_message != last_message:
                send_message(bot, error_message)
                last_message: str = error_message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
