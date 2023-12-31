import logging
import requests
import telegram
from requests.exceptions import ConnectionError, ReadTimeout
from retry import retry

from settings import DvmnSettings, LogSettings, TgSettings


POLLING_URL = 'https://dvmn.org/api/long_polling/'


logger = logging.getLogger(__name__)


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot


    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


@retry((ReadTimeout, ConnectionError),
       delay=0, max_delay=3600, backoff=2, jitter=1, )
def persistent_request(url, params, headers):
    logger.debug(f'Send request with {params=}')
    response = requests.get(url, params=params, headers=headers, )
    response.raise_for_status()
    logger.debug(f"Получили ответ. {response.json()=}")
    return response


def check_status(dvmn_token):
    params = {}
    headers = {"Authorization": f"Token {dvmn_token}", }
    while True:
        response = persistent_request(POLLING_URL, params, headers, )
        payload = response.json()
        match payload['status']:
            case 'timeout':
                params['timestamp'] = payload['timestamp_to_request']
                continue
            case 'found':
                params['timestamp'] = payload['last_attempt_timestamp']
                yield payload["new_attempts"]
            case _:
                raise Exception('Неизвестный статус ответа.'
                                f'Ответ сервера: {payload}')


if __name__ == '__main__':
    log = LogSettings()
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, log.level.upper(), None),
    )
    tg_settings = TgSettings()
    dvmn_settings = DvmnSettings()
    bot = telegram.Bot(token=f'{tg_settings.bot_token}')
    logger.addHandler(TelegramLogsHandler(bot, tg_settings.chat_id))
    logger.info('Start logging')
    while True:
        try:
            for changes in check_status(dvmn_settings.token):
                message = "Статус некоторых проверок изменился! " \
                        "Детали из ответа сервера:\n"
                for attempt in changes:
                    negation = ''
                    if attempt["is_negative"]:
                        negation = 'не '
                    message += f'Название урока: {attempt["lesson_title"]}\n' \
                        f'Ссылка на урок: {attempt["lesson_url"]}\n' \
                        f'Задание {negation}принято'
                bot.send_message(text=message, chat_id=tg_settings.chat_id)
        except Exception as error:
            logger.error(error)
