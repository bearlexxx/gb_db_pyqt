import dis


class ServerMaker(type):
    """
    - ЦЕЛЬ -
    Реализовать метакласс ServerVerifier, выполняющий базовую проверку класса «Сервер»:
    * отсутствие вызовов connect для сокетов;
    * использование сокетов для работы по TCP.
    """

    def __init__(cls, clsname, bases, clsdict):
        methods = []
        methods_2 = []
        attrs = []
        for func in clsdict:
            try:
                ret = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_METHOD':
                        if i.argval not in methods_2:
                            methods_2.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            attrs.append(i.argval)
        if 'connect' in methods:
            raise TypeError('Использование метода connect недопустимо в серверном классе')
        if not ('SOCK_STREAM' in methods and 'AF_INET' in methods):
            raise TypeError('Некорректная инициализация сокета.')

        print(f'Проверки метаклассом {__class__.__name__} пройдены успешно!')

        super().__init__(clsname, bases, clsdict)


class ClientMaker(type):
    """
    Реализовать метакласс ClientVerifier, выполняющий базовую проверку класса «Клиент»:
    * отсутствие вызовов accept и listen для сокетов;
    * использование сокетов для работы по TCP;
    * отсутствие создания сокетов на уровне классов, то есть отсутствие конструкций такого вида:
    """

    def __init__(cls, clsname, bases, clsdict):
        methods = []
        for func in clsdict:
            try:
                ret = dis.get_instructions(clsdict[func])
            except TypeError:
                pass
            else:
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)

        for command in ('accept', 'listen', 'socket'):
            if command in methods:
                raise TypeError('В классе обнаружено использование запрещённого метода')
        if 'get_message' in methods or 'send_message' in methods:
            pass
        else:
            raise TypeError('Отсутствуют вызовы функций, работающих с сокетами.')
        super().__init__(clsname, bases, clsdict)
