import json

from common.variables import MAX_PACKET_LENGTH, ENCODING
from common.decorators import log


@log
def get_message(client):
    data_bytes = client.recv(MAX_PACKET_LENGTH)
    if not isinstance(data_bytes, bytes):
        raise ValueError('Получили НЕ байтовые данные')

    data_str = data_bytes.decode(ENCODING)
    if not isinstance(data_str, str):
        raise ValueError('Полученное сообщение не является строкой')

    if data_str == '':
        raise TypeError('Получено пустое сообщение')

    data_dict = json.loads(data_str)
    if not isinstance(data_dict, dict):
        raise ValueError('Аргумент функции должен быть словарём.')

    return data_dict


@log
def send_message(sock, message):
    if not isinstance(message, dict):
        raise TypeError('Аргумент функции должен быть словарём.')

    message_bytes = json.dumps(message).encode(ENCODING)
    sock.send(message_bytes)
