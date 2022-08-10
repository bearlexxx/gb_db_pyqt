import inspect
from functools import wraps
import logging
import logs.client_log_config
import logs.server_log_config
import sys


def log(func):
    logger = 'app.server' if 'server.py' in sys.argv[0] else 'app.client'
    LOG = logging.getLogger(logger)

    @wraps(func)
    def wrap(*args, **kwargs):
        f = func(*args, **kwargs)

        current_frame = inspect.currentframe()
        caller_frame = current_frame.f_back
        code_obj = caller_frame.f_code
        code_obj_name = code_obj.co_name

        LOG.info(f'вызов {func.__name__}() с параметрами {args} {kwargs} из функции {code_obj_name}')

        return f

    return wrap
