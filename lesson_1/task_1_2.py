"""
Написать функцию host_range_ping() (возможности которой основаны на функции из примера 1)
для перебора ip-адресов из заданного диапазона. Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
"""

from ipaddress import ip_address

from lesson_1.task_1_1 import host_ping


def host_range_ping(ip_addr_start, ip_addr_range):
    try:
        ip_start_ob = ip_address(ip_addr_start)
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
    host_ping(list_ips, True)


if __name__ == "__main__":
    ip_start = input('Введите первоначальный IPv4 адрес: ')
    ip_range = int(input('Количество адресов для проверки: '))

    host_range_ping(ip_start, ip_range)
