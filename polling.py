import requests
from time import sleep
import telegram
from environs import Env


env = Env()
env.read_env()

DVMN_TOKEN = env.str('DVMN_TOKEN')
TG_BOT_TOKEN = env.str('TG_BOT_TOKEN')
TG_CHAT_ID = env.str('TG_CHAT_ID')

POLLING_URL = 'https://dvmn.org/api/long_polling/'

CONNECTION_ERROR_DELAY = 90


def start_devman_polling(timestamp):
    params = {'timestamp': timestamp}
    headers = {"Authorization": f"Token {DVMN_TOKEN}", }
    while True:
        print(f"Запрашиваем наличие изменений. {params}")
        try:
            res = requests.get(
                POLLING_URL,
                headers=headers,
                params=params, )
            res.raise_for_status()
        except requests.exceptions.ReadTimeout:
            continue
        except requests.exceptions.ConnectionError:
            sleep(CONNECTION_ERROR_DELAY)
            continue

        answer = res.json()
        match answer['status']:
            case 'timeout':
                params['timestamp'] = answer['timestamp_to_request']
                continue
            case 'found':
                return answer
            case _:
                raise Exception('Неизвестный статус ответа.'
                                f'Ответ сервера: {answer}')


if __name__ == '__main__':
    bot = telegram.Bot(token=f'{TG_BOT_TOKEN}')
    timestamp = None
    while True:
        changes = start_devman_polling(timestamp)
        message = "Статус некоторых проверок изменился! " \
                  "Детали из ответа сервера:\n"
        for attempt in changes["new_attempts"]:
            message += f'Название урока: {attempt["lesson_title"]}\n' \
                f'Ссылка на урок: {attempt["lesson_url"]}\n' \
                f'Задание {"не" if attempt["is_negative"] else ""}принято'
        bot.send_message(text=message, chat_id=TG_CHAT_ID)

        timestamp = changes['last_attempt_timestamp']
