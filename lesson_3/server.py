""" Сервер """

import argparse
import time
import threading
from select import select
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from common.variables import DEFAULT_PORT, MAX_CONNECTIONS, ACTION, USER, ACCOUNT_NAME, \
    TIME, RESPONSE, ERROR, PRESENCE, CONNECTION_TIMEOUT, MESSAGE, MESSAGE_TEXT, SENDER, DESTINATION, EXIT
from common.utils import get_message, send_message
from common.decorators import log
import logging
import logs.server_log_config
from common.descriptors import Port
from common.metaclasses import ServerMaker
from db.server_db import ServerDB

LOG = logging.getLogger('app.server')


@log
def arg_parser():
    """
    Разбор параметров командной строки.
    server.py -p 8888 -a 127.0.0.1
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', default='', nargs='?',
                        help=f'Server address. Default - all net interfaces')
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?',
                        help=f'Server port 1024-65535. Default {DEFAULT_PORT}')
    args = parser.parse_args()

    return args.a, args.p


class Server(threading.Thread, metaclass=ServerMaker):
    port = Port()

    def __init__(self, listen_address, listen_port, database):
        self.addr = listen_address
        self.port = listen_port
        self.database = database
        self.sock = None
        self.all_clients = []
        self.messages = []
        self.names = {}
        super().__init__()

    def init_socket(self):
        """ Подготовка сокета """
        s = socket(AF_INET, SOCK_STREAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind((self.addr, self.port))
        s.settimeout(CONNECTION_TIMEOUT)
        print(f'Server ready. Listen connect on {self.addr}:{self.port}')
        LOG.info(f'Server start. Listen connect on {self.addr}:{self.port}')

        self.sock = s
        self.sock.listen(MAX_CONNECTIONS)

    def run(self):
        self.init_socket()

        while True:
            try:
                client_socket, client_address = self.sock.accept()
            except OSError as err:  # timeout
                pass
            else:
                LOG.info(f'Получен запрос на соединение от {str(client_address)}')
                print(f"Получен запрос на соединение от {str(client_address)}")
                self.all_clients.append(client_socket)

            wait = 0.1
            clients_read = []
            clients_write = []

            if self.all_clients:
                try:
                    clients_read, clients_write, errors = select(self.all_clients, self.all_clients, [], wait)
                except OSError:
                    pass
                except Exception as e:
                    print('ошибка в select:', e)

            if clients_read:
                for client_with_message in clients_read:
                    try:
                        print(f'пришло сообщение от {client_with_message.getpeername()}')
                        self.process_client_message(get_message(client_with_message), client_with_message)

                    except OSError:
                        print('Отправитель отключился')
                        LOG.info(f'Отправитель отключился от сервера.')
                        self.all_clients.remove(client_with_message)
                        client_with_message.close()
                    except Exception as e:
                        print('Отправитель отключился', client_with_message.getpeername())
                        LOG.info(f'Отправитель {client_with_message.getpeername()} отключился от сервера.')
                        self.all_clients.remove(client_with_message)
                        client_with_message.close()

            if self.messages:
                for _ in range(len(self.messages)):
                    msg = self.messages.pop()

                    try:
                        self.process_message(msg, clients_write)
                    except Exception:
                        LOG.info(f'Связь с клиентом с именем {msg[DESTINATION]} была потеряна')
                        self.all_clients.remove(self.names[msg[DESTINATION]])
                        self.names[msg[DESTINATION]].close()
                        del self.names[msg[DESTINATION]]

    def process_message(self, message, listen_socks):
        """
        Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение
        и слушающие сокеты. Список зарегистрированных пользователей берет из глобального __init__.
        Ничего не возвращает.
        :param message:
        :param listen_socks:
        :return:
        """

        if message[DESTINATION] not in self.names:
            message_dict = {
                ACTION: MESSAGE,
                SENDER: 'Server',
                DESTINATION: message[SENDER],
                TIME: time.time(),
                MESSAGE_TEXT: f'Пользователь {message[DESTINATION]} не зарегистрирован.'
            }
            send_message(self.names[message[SENDER]], message_dict)
            LOG.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, отправка сообщения невозможна.')
            return

        if self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError

        send_message(self.names[message[DESTINATION]], message)
        LOG.info(f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.')

    def process_client_message(self, message, sock):
        """
        Обрабатывает принятые сообщения от клиентов на соответствие протоколу JIM и возвращает словарь с ответом.
        messages, all_clients, names берутся из __init__
        :param message: словарь с новым сообщением
        :param sock: сокет  с новым сообщением
        :return:
        """

        if __debug__:
            LOG.debug(f'Разбор входящего сообщения: {message}')

        if ACTION not in message or TIME not in message:
            if __debug__:
                LOG.warning(f'Пришли неизвестные данные - {message}. Ответ - Bad request')
            return {RESPONSE: 400, ERROR: 'Bad request'}

        return_code = 200

        if message[ACTION] == PRESENCE and ACCOUNT_NAME in message[USER]:
            new_user = message[USER][ACCOUNT_NAME]

            if new_user not in self.names.keys():
                if __debug__:
                    LOG.debug(f'Зарегистрировали нового пользователя {new_user}')
                self.names[new_user] = sock
                client_ip, client_port = sock.getpeername()
                self.database.user_login(new_user, client_ip, client_port)
                send_message(sock, {RESPONSE: return_code})
                return True
            else:
                return_code = 400
                if __debug__:
                    LOG.debug(f'Пользователь уже добавлен. Код {return_code}')
                send_message(sock, {RESPONSE: return_code, ERROR: f'Пользователь {new_user} уже зарегистрирован.'})
                return True

        elif message[ACTION] == MESSAGE and MESSAGE_TEXT in message and DESTINATION in message and SENDER in message:
            self.messages.append(message)

            # if __debug__:
            #     LOG.debug(f'Ответ клиенту на {message[ACTION]}. Код {return_code}')
            # send_message(sock, {RESPONSE: return_code})
            return True

        elif message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.all_clients.remove(self.names[message[ACCOUNT_NAME]])
            del self.names[message[ACCOUNT_NAME]]
            LOG.info(f'Пользователь {message[ACCOUNT_NAME]} прислал команду выхода')
            sock.close()
            return

        return_code = 400
        LOG.info(f'Ответ клиенту на {PRESENCE}. Код {return_code}. Неизвестный {ACTION}')
        send_message(sock, {RESPONSE: return_code, ERROR: f'Action {message[ACTION]} not support'})
        return True


def print_help():
    print()
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    listen_address, listen_port = arg_parser()

    database = ServerDB()

    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    time.sleep(0.5)
    print_help()

    while True:
        command = input('Введите команду: ')

        if command == 'help':
            print_help()
        elif command == 'exit':
            break
        elif command == 'users':
            for user in sorted(database.users_list()):
                print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
        elif command == 'loghist':
            name = input('Введите имя пользователя для просмотра истории. '
                         'Для вывода всей истории, просто нажмите Enter: ')
            for user in sorted(database.login_history(name)):
                print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
        else:
            print('Команда не распознана.')


if __name__ == '__main__':
    main()
