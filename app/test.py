import requests

import dotenv
import os


dotenv.load_dotenv()
APP_URL = os.environ.get('APP_URL')


def test_api_active_get():
    json = {
        'api_key': '8f6673a8-2408-4b8f-8892-758daa91a447'
    }
    response = requests.get(APP_URL + 'api/active', json=json)
    print(response)
    print(response.json())


def test_api_active_post():
    status_update = {
        'api_key': 'asadsaffdssfd',
        'id': 1,
        'status': 'failed',
    }
    response = requests.post(APP_URL + 'api/active', json=status_update)


if __name__ == '__main__':
    test_api_active_get()
    # test_api_active_post()
