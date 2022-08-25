""" Клиент """

import json
import time
import argparse
import threading
from socket import socket, AF_INET, SOCK_STREAM
from common.utils import get_message, send_message
from common.variables import *
from common.decorators import log
from common.errors import ServerError
import logging
import logs.client_log_config
from common.metaclasses import ClientMaker
from db.client_db import ClientDB

LOG = logging.getLogger('app.client')

sock_lock = threading.Lock()
database_lock = threading.Lock()


class ClientSender(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def create_exit_message(self):
        message_dict = {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

        try:
            send_message(self.sock, message_dict)
            LOG.info(f'Завершение работы по команде пользователя.')
            time.sleep(0.5)
            exit(1)
        except (ConnectionResetError, ConnectionError, ConnectionAbortedError) as e:
            print(e)
            LOG.critical('Потеряно соединение с сервером.')
            exit(1)

    def create_message(self):
        while True:
            to_user = input('Введите получателя сообщения: ')
            if to_user:
                break

        while True:
            message = input('Введите сообщение для отправки: ')
            if message:
                break

        with database_lock:
            if not self.database.check_user(to_user):
                LOG.error(f'Попытка отправить сообщение '
                          f'незарегистрированому получателю: {to_user}')
                return

        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }

        if __debug__:
            LOG.debug(f'Сформирован словарь сообщения: {message_dict}')

        with database_lock:
            self.database.save_message(self.account_name, to_user, message)

        with sock_lock:
            try:
                send_message(self.sock, message_dict)
                LOG.info(f'Отправлено сообщение для пользователя {to_user}')
                print('Сообщение отправлено.')
            except (ConnectionResetError, ConnectionError, ConnectionAbortedError, OSError) as e:
                print(e)
                if e.errno:
                    LOG.critical('Потеряно соединение с сервером.')
                    exit(1)
                else:
                    LOG.error('Не удалось передать сообщение. Таймаут соединения')

    def run(self):
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()

            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                with sock_lock:
                    self.create_exit_message()
                    break

            elif command == 'contacts':
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)

            elif command == 'edit':
                self.edit_contacts()

            elif command == 'history':
                self.print_history()

            else:
                print('Команда не распознана, попробуйте снова. help - вывести поддерживаемые команды.')

    def print_help(self):
        help_message = """Поддерживаемые команды:
        message - отправить сообщение. Кому и текст будет запрошены отдельно.
        history - история сообщений
        contacts - список контактов
        edit - редактирование списка контактов
        help - вывести подсказки по командам
        exit - выход из программы
        """
        print(help_message)

    def edit_contacts(self):
        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            edit = input('Введите имя удаляемого контакта: ')
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    LOG.error('Попытка удаления несуществующего контакта.')
        elif ans == 'add':
            edit = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except ServerError:
                        LOG.error('Не удалось отправить информацию на сервер.')

    def print_history(self):
        ask = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock:
            if ask == 'in':
                history_list = self.database.get_history(to_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} '
                          f'от {message[3]}:\n{message[2]}')
            elif ask == 'out':
                history_list = self.database.get_history(from_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} '
                          f'от {message[3]}:\n{message[2]}')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]},'
                          f' пользователю {message[1]} '
                          f'от {message[3]}\n{message[2]}')


class ClientReader(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def run(self):
        while True:

            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock)
                except TypeError:

                    pass
                except ValueError as e:
                    LOG.error(f'Не удалось декодировать полученное сообщение. {e}')
                except OSError as err:
                    if err.errno:
                        LOG.critical(f'Потеряно соединение с сервером.')
                        break
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                    LOG.critical(f'Потеряно соединение с сервером.')
                    break

                else:
                    if ACTION in message and message[ACTION] == MESSAGE and SENDER in message \
                            and DESTINATION in message \
                            and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                        print(f'\nПолучено сообщение от пользователя {message[SENDER]}:'
                              f'\n{message[MESSAGE_TEXT]}')

                        with database_lock:
                            try:
                                self.database.save_message(message[SENDER],
                                                           self.account_name,
                                                           message[MESSAGE_TEXT])
                            except Exception as e:
                                print(e)
                                LOG.error('Ошибка взаимодействия с базой данных')

                        LOG.info(f'Получено сообщение от пользователя {message[SENDER]}: {message[MESSAGE_TEXT]}')
                    else:
                        LOG.error(f'Получено некорректное сообщение с сервера: {message}')


@log
def process_ans(message):
    """
    :param message:
    :return:
    """
    if RESPONSE in message:
        if 200 <= message[RESPONSE] <= 210:
            if __debug__:
                LOG.debug(f'Успешный ответ от сервера с кодом {message[RESPONSE]}')
            return '200 : OK'
        elif message[RESPONSE] >= 400:
            raise ServerError(f'{message[RESPONSE]} : {message[ERROR]}')

        LOG.error(f'Ошибочный ответ сервера: код {message[RESPONSE]} - {message[ERROR]}')
        return f'Error code {message[RESPONSE]} : {message[ERROR]}'

    LOG.error(f'Не верный ответ сервера! Не подошел ни один формат ответа. {message}')
    raise ValueError(f'В принятом словаре отсутствуют обязательные поля')


@log
def create_presence(sock, account_name='Guest'):
    """
    Создает словарь с сообщением к серверу о присутствии клиента онлайн и отправляет его.
    :param sock:
    :param account_name:
    :return:
    """

    message_dict = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }

    if __debug__:
        LOG.debug(f'Создан запрос присутствия для клиента {account_name}')

    try:
        send_message(sock, message_dict)
        LOG.info(f'Отправлен запрос присутствия {account_name}')
    except (ConnectionResetError, ConnectionError, ConnectionAbortedError) as e:
        print(e)
        LOG.critical('Потеряно соединение с сервером.')
        exit(1)


@log
def arg_parser():
    """
    client.py 127.0.0.1 8888 -m send
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?',
                        help=f'Server address. Default {DEFAULT_IP_ADDRESS}')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?',
                        help=f'Server port 1024-65535. Default {DEFAULT_PORT}')
    parser.add_argument('-n', '--name', default='', nargs='?', help='имя пользователя в чате')
    args = parser.parse_args()

    if args.port < 1024 or args.port > 65536:
        LOG.warning('Номер порта должен быть указан в пределах 1024 - 65635')
        exit(1)

    return args.addr, args.port, args.name


def contacts_list_request(sock, name):
    LOG.debug(f'Запрос контакт листа для пользователя {name}')
    req = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        USER: name
    }
    LOG.debug(f'Сформирован запрос {req}')
    send_message(sock, req)
    ans = get_message(sock)
    LOG.debug(f'Получен ответ {ans}')
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


def add_contact(sock, username, contact):
    LOG.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта')
    print('Удачное создание контакта.')


def user_list_request(sock, username):
    LOG.debug(f'Запрос списка известных пользователей {username}')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


def remove_contact(sock, username, contact):
    LOG.debug(f'Создание контакта {contact}')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')


def database_load(sock, database, username):
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        LOG.error('Ошибка запроса списка известных пользователей.')
    else:
        database.add_users(users_list)

    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        LOG.error('Ошибка запроса списка контактов.')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


def main():
    server_address, server_port, client_name = arg_parser()

    while True:
        if not client_name:
            client_name = input('Имя пользователя в чате: ')
        else:
            break

    LOG.info(f'Клиент чата запущен со следующими параметрами:'
             f' {server_address}:{server_port}, Пользователь: {client_name}')

    try:
        s = socket(AF_INET, SOCK_STREAM)
        s.settimeout(1)
        s.connect((server_address, server_port))
    except (ConnectionRefusedError, ConnectionError):
        LOG.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        exit(1)

    create_presence(s, client_name)

    try:
        msg_in = get_message(s)
        print(f'Установлено соединение с сервером. Ответ {process_ans(msg_in)}. Пользователь: {client_name}')
    except ServerError as e:
        print(f'Server error {e}')
        LOG.error(e)
        s.close()
        exit(1)
    except TypeError as e:
        LOG.critical(e)
        s.close()
        exit(1)
    except(ValueError, json.JSONDecodeError) as e:
        LOG.error(e)
        s.close()
        exit(1)

    database = ClientDB(client_name)
    database_load(s, database, client_name)

    module_receiver = ClientReader(client_name, s, database)
    module_receiver.daemon = True
    module_receiver.start()

    module_sender = ClientSender(client_name, s, database)
    module_sender.daemon = True
    module_sender.start()

    if __debug__:
        LOG.debug('Потоки запущены')

    while True:
        time.sleep(0.5)
        if module_receiver.is_alive() and module_sender.is_alive():
            continue
        break


if __name__ == '__main__':
    main()
