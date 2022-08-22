"""Launcher for Windows"""

from subprocess import Popen, CREATE_NEW_CONSOLE
from time import sleep

P_LIST = []
clients_count = int(input(f'Сколько клиентов запустить?: '))

while True:
    USER = input(f'Запустить {clients_count} клиентов (s) / Закрыть клиентов (x) / Выйти (q) ')

    if USER == 'q':
        break

    elif USER == 's':
        P_LIST.append(Popen('python server.py', creationflags=CREATE_NEW_CONSOLE))

        for i in range(clients_count):
            P_LIST.append(Popen(f'python client.py -n guest{i + 1}', creationflags=CREATE_NEW_CONSOLE))

        print(f'Запущено {clients_count} клиентов')
    elif USER == 'x':
        for p in P_LIST:
            p.kill()
        P_LIST.clear()
