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
    ResponceTypeError,
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


def check_tokens():
    """Проверяет наличие необходимых для работы программы токенов."""
    tokens_bool = True
    for token in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if not token:
            tokens_bool = False
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {token}')
    return tokens_bool


def get_api_answer(timestamp):
    """
    Делает запрос к API Яндекс.Домашки.
    Принимает данные для запроса, возвращает ответ сервера в формате Python.
    """
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
    except requests.RequestException as error:
        raise RequestExceptionError(
            f'Ошибка при запросе к API: {error}') from error
    except Exception as error:
        raise RequestExceptionError(
            f'Ошибка при запросе к API: {error}') from error
    else:
        if response.status_code != HTTPStatus.OK:
            raise requests.HTTPError('Статус страницы не равен 200')

    return response.json()


def check_response(response):
    """
    Проверяет ответ API на соответствие документации.
    Принимает ответ сервера,
    возвращает список домашних работ, полученных из запроса.
    """
    if not isinstance(response, dict):
        raise ResponceTypeError(
            f'В ответе получен тип данных {type(response)}. '
            'Ожидался dict.'
        )
    if 'homeworks' not in response:
        raise EmptyResponseError('В ответе нет ключа homeworks')
    if 'current_date' not in response:
        raise EmptyResponseError('В ответе нет ключа current_date')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise ResponceTypeError(
            f'В homeworks получен тип данных {type(homeworks)}. '
            'Ожидался list.'
        )

    return homeworks


def parse_status(homework):
    """
    Извлекает информацию о статусе домашней работы.
    Принимает последнюю работу, получившую статус,
    возвращает строку со статусом проверки работы.
    """
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if not status:
        raise EmptyResponseError('Пустое значение status')
    if not homework_name:
        raise EmptyResponseError('Пустое значение homework_name')
    if status not in HOMEWORK_VERDICTS:
        raise UndocumentedStatusError(
            f'Неизвестный статус домашней работы - {status}'
        )
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """
    Отправляет сообщение с результатом пользователю.
    Принимает объект бота и текст сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logging.exception(
            f'Не удалось отправить сообщение {message}', error, exc_info=True)
    else:
        logging.debug('Сообщение отправлено')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Отсутствует токен!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 1699574400  # 10 ноября
    rev_msg = ''
    while True:
        try:
            payload = {'from_date': timestamp}
            response = get_api_answer(payload)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Новых статусов нет'
        except (RequestExceptionError, requests.HTTPError) as error:
            message = f'Ошибка при запросе к API: {error}'
            logging.error(message, error, exc_info=True)
        except (ResponceTypeError, EmptyResponseError) as error:
            message = f'Ошибка обработки данных из запроса: {error}'
            logging.error(message, error, exc_info=True)
        except UndocumentedStatusError as error:
            message = 'Неизвестный статус домашней работы'
            logging.error(message, error, exc_info=True)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.critical(message)
            raise error(message)
        else:
            if message != rev_msg:
                send_message(bot, message)
                rev_msg = message
            else:
                logging.debug(
                    f'Новых статусов нет, последнее обновление: {message}'
                )
        finally:
            timestamp = response.get('current_date')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':

    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
        level=logging.DEBUG,
        handlers=[logging.FileHandler('homework.log', encoding='UTF-8'),
                  logging.StreamHandler(sys.stdout)]
    )

    main()
