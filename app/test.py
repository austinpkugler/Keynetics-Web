import requests

import dotenv
import os


dotenv.load_dotenv()
APP_URL = os.environ.get('APP_URL')


def test_api_active_get():
    json = {
        'api_key': 'demo'
    }
    response = requests.get(APP_URL + '/api/active', json=json)
    print(response.json())


def test_api_active_post():
    status_update = {
        'api_key': 'demo',
        'id': 1,
        'status': 'failed',
    }
    response = requests.post(APP_URL + '/api/active', json=status_update)
    print(response.json())


if __name__ == '__main__':
    test_api_active_get()
    test_api_active_post()
