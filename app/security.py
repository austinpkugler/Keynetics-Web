from flask import request

import functools

from app import models


def is_valid_api_key(api_key):
    return models.APIKey.query.filter_by(key=api_key).first() is not None


def api_key_required(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        data = request.get_json(force=True)
        if data:
            api_key = data['api_key']
            if is_valid_api_key(api_key):
                return func(*args, **kwargs)
            else:
                return {'response': 403, 'message': 'The provided API key is not valid'}, 403
        else:
            return {'response': 400, 'message': 'Please provide an API key'}, 400
    return decorator
