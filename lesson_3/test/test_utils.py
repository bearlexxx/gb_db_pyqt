import json
import sys
import os
import unittest

sys.path.append(os.path.join(os.getcwd(), '..'))

from common.variables import *
from common.utils import *


class TestSocket:
    """ Тестовый сокет для методов send, recv. При создании экземпляра требуется словарь с данными. """

    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.encoded_msg = None
        self.received_msg = None

    def send(self, msg):
        """ Эмуляция отправки сообщения с сохранением данных в атрибутах объекта """
        json_test_msg = json.dumps(self.test_dict)
        self.encoded_msg = json_test_msg.encode(ENCODING)
        self.received_msg = msg

    def recv(self, max_len):
        """ Эмуляция получения данных из сокета """
        json_test_msg = json.dumps(self.test_dict)
        return json_test_msg.encode(ENCODING)


class TestClientClass(unittest.TestCase):
    """ Тестирование функций утилит """

    test_dict_send = {ACTION: PRESENCE, TIME: 122.33, USER: {ACCOUNT_NAME: 'Stuff'}}
    test_dict_recv_ok = {RESPONSE: 200}
    test_dict_recv_error = {RESPONSE: 400, ERROR: 'Bad Request'}

    def test_send_message_ok(self):
        """ Проверка корректной отправки в сокет через send_message() """
        test_socket = TestSocket(self.test_dict_send)
        send_message(test_socket, self.test_dict_send)
        self.assertEqual(test_socket.received_msg, test_socket.encoded_msg)

    def test_send_message_exception(self):
        """ Проверка отправки в сокет через send_message() произвольной строки """
        test_socket = TestSocket(self.test_dict_send)
        self.assertRaises(TypeError, send_message, test_socket, 'string string')

    def test_get_message_ok(self):
        """ Проверка корректного ответа функции get_message() """
        test_socket = TestSocket(self.test_dict_recv_ok)
        self.assertEqual(get_message(test_socket), self.test_dict_recv_ok)

    def test_get_message_error(self):
        """ Проверка корректного ответа функции get_message() """
        test_socket = TestSocket(self.test_dict_recv_error)
        self.assertEqual(get_message(test_socket), self.test_dict_recv_error)


if __name__ == '__main__':
    unittest.main()