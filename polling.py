import requests
from time import sleep
import telegram
from environs import Env


REVIEWS_URL = 'https://dvmn.org/api/user_reviews/'
POLLING_URL = 'https://dvmn.org/api/long_polling/'

CONNECTION_ERROR_DELAY = 90
MAX_TIMEOUT_COUNT = 3


def review_list(dvmn_token: str):
    url = REVIEWS_URL
    headers = {"Authorization": f"Token {dvmn_token}", }
    reviews = {}
    while True:
        res = requests.get(url, headers=headers, )
        res.raise_for_status()
        results = res.json()['results']
        if res.status_code != requests.codes.ok:
            raise Exception('Неизвестный статус ответа.'
                            f'Ответ сервера: {res.json()}')

        for result in results:
            if result['lesson_title'] not in reviews:
                reviews[result['lesson_title']] = {
                    'url': result['lesson_url'],
                    'finished': False
                }
            reviews[result['lesson_title']][result['submitted_at']] = \
                result['is_negative']
            reviews[result['lesson_title']]['finished'] = \
                reviews[result['lesson_title']]['finished'] \
                or not result['is_negative']

        url = res.json()['next']
        if not url:
            break
    return reviews


def devman_polling(token):
    params = {}
    headers = {"Authorization": f"Token {token}", }
    timeout_count = 0
    while True:
        print(f"Запрашиваем наличие изменений. {params}")
        try:
            res = requests.get(
                POLLING_URL,
                headers=headers,
                params=params, )
            res.raise_for_status()
        except requests.exceptions.ReadTimeout:
            timeout_count += 1
            print(f"Сервер не ответил {timeout_count} раз подряд")
            continue
        except requests.exceptions.ConnectionError:
            print("CONNECTION ERROR. Делаем паузу "
                  f"{CONNECTION_ERROR_DELAY} секунд")
            sleep(CONNECTION_ERROR_DELAY)
            continue

        timeout_count = 0

        match res.json()['status']:
            case 'timeout':
                params['timestamp'] = res.json()['timestamp_to_request']
                continue
            case 'found':
                print('Получен ответ об изменении статуса', res.json())
                return res.json()
            case _:
                raise Exception('Неизвестный статус ответа.'
                                f'Ответ сервера: {res.json()}')


if __name__ == '__main__':
    env = Env()
    env.read_env()

    DVMN_TOKEN = env.str('DVMN_TOKEN')
    BOT_TOKEN = env.str('BOT_TOKEN')
    CHAT_ID = env.str('CHAT_ID')

    text = ''
    reviews = review_list(DVMN_TOKEN)
    text += '\nЗавершённые работы:'
    for review in reviews:
        if reviews[review]['finished']:
            text += f'\n\t {review}'
    text += '\nНезавершённые работы:'
    for review in reviews:
        if not reviews[review]['finished']:
            text += f'\n\t {review}'
    bot = telegram.Bot(token=f'{BOT_TOKEN}')
    bot.send_message(text=text, chat_id=CHAT_ID)

    changes = devman_polling(DVMN_TOKEN)

    message = "Статус некоторых проверок изменился! " \
              "Детали из ответа сервера:\n"
    for attempt in changes["new_attempts"]:
        message += f'Название урока: {attempt["lesson_title"]}\n'
        message += f'Ссылка на урок: {attempt["lesson_url"]}\n'
        message += f'Задание {"не" if attempt["is_negative"] else ""} принято'

    bot = telegram.Bot(token=f'{BOT_TOKEN}')
    bot.send_message(text=message, chat_id=CHAT_ID)
