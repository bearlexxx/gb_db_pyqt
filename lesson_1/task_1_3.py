"""
Написать функцию host_range_ping_tab(), возможности которой основаны на функции из примера 2.
Но в данном случае результат должен быть итоговым по всем ip-адресам, представленным в табличном формате
(использовать модуль tabulate).
"""

from ipaddress import IPv4Address
from task_1_1 import host_ping
from time import perf_counter
from tabulate import tabulate


def host_range_ping_tab(ip_addr_start, ip_addr_range):
    try:
        ip_start_ob = IPv4Address(ip_addr_start)
    except ValueError:
        print('Неверный формат ip адреса')
        return False

    if not isinstance(ip_addr_range, int):
        raise ValueError('Неправильный формат количества адресов')

    max_ip_range = 255 - int(ip_addr_start.split('.')[-1])
    if ip_addr_range > max_ip_range:
        print(f'Превышен диапазон адресов проверки, необходимо меньше {max_ip_range}')
        return False

    list_ips = [str(ip_start_ob + i) for i in range(ip_addr_range)]

    print('Проверка запущена...')

    time_start = perf_counter()
    result_list = host_ping(list_ips)
    time_work = perf_counter() - time_start
    print(f"Время работы: {time_work:0.2f} (сек)")
    print()

    list_ok = []
    list_err = []

    for addr in result_list:
        if addr[1]:
            list_ok.append(addr[0])
        else:
            list_err.append(addr[0])

    tabulate_dict = {'Reachable': list_ok, 'Unreachable': list_err}
    print(tabulate(tabulate_dict, headers='keys', tablefmt='grid'))


if __name__ == "__main__":
    ip_start = input('Введите первоначальный IPv4 адрес: ')
    ip_range = int(input('Количество адресов для проверки: '))

    host_range_ping_tab(ip_start, ip_range)
