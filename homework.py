import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram

from dotenv import load_dotenv

from exceptions import (
    RequestExceptionError,
    UndocumentedStatusError,
    EmptyResponseError
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
    level=logging.DEBUG,
    handlers=[logging.FileHandler('homework.log', encoding='UTF-8'),
              logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def check_tokens():
    """
    Проверяет наличие необходимых для работы программы токенов
    """
    tokens_bool = True
    for token in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if token is None:
            tokens_bool = False
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {token}')
    return tokens_bool


def get_api_answer(timestamp):
    """
    Делает запрос к API Яндекс.Домашки,
    возвращает ответ сервера в формате Python
    """
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
    except requests.RequestException as error:
        logger.error(f'Ошибка при запросе к API: {error}')
        raise RequestExceptionError() from error
    except Exception as error:
        logger.error(f'Ошибка при запросе к API: {error}')
        raise error
    else:
        if response.status_code != HTTPStatus.OK:
            logger.error('Статус страницы не равен 200')
            raise requests.HTTPError('Статус страницы не равен 200')

    return response.json()


def check_response(response):
    """
    Проверяет ответ API на соответствие документации,
    возвращает список домашних работ, полученных из запроса
    """
    if not isinstance(response, dict):
        logger.error('Ответ не является словарем')
        raise TypeError('Ответ не является словарем')
    if 'homeworks' not in response:
        logger.error('В ответе нет ключа homeworks')
        raise EmptyResponseError('В ответе нет ключа homeworks')
    if 'current_date' not in response:
        logger.error('В ответе нет ключа current_date')
        raise EmptyResponseError('В ответе нет ключа current_date')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        logger.error('homeworks не является list')
        raise TypeError('homeworks не является list')

    return homeworks


def parse_status(homework):
    """
    Извлекает информацию о статусе домашней работы,
    возвращает строку со статусом
    """
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if status is None:
        logger.error('Ошибка пустое значение status: ', status)
        raise EmptyResponseError('Ошибка пустое значение status: ', status)
    if homework_name is None:
        logger.error('Ошибка пустое значение homework_name: ', homework_name)
        raise EmptyResponseError(
            'Ошибка пустое значение homework_name: ',
            homework_name
        )
    if status not in HOMEWORK_VERDICTS:
        logger.error(f'Неизвестный статус домашней работы - {status}')
        raise UndocumentedStatusError(
            f'Неизвестный статус домашней работы - {status}'
        )
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """
    Отправляет сообщение с результатом пользователю
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logger.error(
            f'Сообщение не отправлено: {error}')
    else:
        logger.debug('Сообщение отправлено')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Отсутствует токен!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0  # предлож вариант: int(time.time())
    while True:
        try:
            payload = {'from_date': timestamp}
            response = get_api_answer(payload)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Новых статусов нет'
                logger.debug(message)
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.critical(message)
            raise error
        finally:
            timestamp = response.get('current_date')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
