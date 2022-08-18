import logging
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

LOG = logging.getLogger('app.server')

try:
    import sqlalchemy

    if __debug__:
        LOG.debug(f'SQLAlchemy: {sqlalchemy.__version__} подключена')
except ImportError:
    LOG.critical('Библиотека SQLAlchemy не найдена')
    exit(13)


#
# PATH = os.path.dirname(os.path.abspath(__file__))
# PATH = os.path.join(PATH, 'server_base.db3')


class ServerDB:
    Base = declarative_base()

    class AllUsers(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        user = Column(String, unique=True)
        last_conn = Column(DateTime)

        def __init__(self, user):
            self.user = user
            self.last_conn = datetime.datetime.now()

    class ActiveUsers(Base):
        __tablename__ = 'users_active'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('users.id'), unique=True)
        ip = Column(String(50))
        port = Column(Integer)
        time_conn = Column(DateTime)

        def __init__(self, user, ip, port):
            self.user = user
            self.ip = ip
            self.port = port
            self.time_conn = datetime.datetime.now()

    class LoginHistory(Base):
        __tablename__ = 'users_login_history'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('users.id'))
        ip = Column(String)
        port = Column(Integer)
        last_conn = Column(DateTime)

        def __init__(self, user, ip, port):
            self.user = user
            self.ip = ip
            self.port = port
            self.last_conn = datetime.datetime.now()

    class UsersContacts(Base):
        __tablename__ = 'users_contacts'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('users.id'))
        contact = Column(String, ForeignKey('users.id'))

        def __init__(self, user, contact):
            self.user = user
            self.contact = contact

    class UsersHistory(Base):
        __tablename__ = 'users_history'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('users.id'))
        sent = Column(Integer)
        accepted = Column(Integer)

        def __init__(self, user):
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        self.engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                    connect_args={'check_same_thread': False})

        self.Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username, ip_address, port):
        rez = self.session.query(self.AllUsers).filter_by(user=username)
        # print(type(rez))
        if rez.count():
            user = rez.first()
            user.last_conn = datetime.datetime.now()
        else:
            user = self.AllUsers(username)
            self.session.add(user)
            self.session.commit()
            user_in_history = self.UsersHistory(user.id)
            self.session.add(user_in_history)

        new_active_user = self.ActiveUsers(user.id, ip_address, port)
        self.session.add(new_active_user)

        history = self.LoginHistory(user.id, ip_address, port)
        self.session.add(history)
        self.session.commit()

    def user_logout(self, username):
        user = self.session.query(self.AllUsers).filter_by(user=username).first()

        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    def process_message(self, sender, recipient):
        sender = self.session.query(self.AllUsers).filter_by(user=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(user=recipient).first().id
        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        recipient_row.accepted += 1

        self.session.commit()

    def add_contact(self, user, contact):
        if user == contact:
            return

        try:
            user_id = self.session.query(self.AllUsers).filter_by(user=user).first().id
            contact_id = self.session.query(self.AllUsers).filter_by(user=contact).first().id
        except AttributeError:
            if __debug__:
                LOG.debug(f'Добавление контакта - юзер {user} или {contact} не найден')
                print(f'Добавление контакта - юзер {user} или {contact} не найден')
            return

        if not contact or self.session.query(self.UsersContacts).filter_by(user=user_id, contact=contact_id).count():
            return

        contact_row = self.UsersContacts(user_id, contact_id)
        self.session.add(contact_row)
        self.session.commit()

    def remove_contact(self, user, contact):
        user = self.session.query(self.AllUsers).filter_by(user=user).first()
        contact = self.session.query(self.AllUsers).filter_by(user=contact).first()

        if not contact:
            return

        self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).delete()
        self.session.commit()

    def get_contacts(self, username):
        user = self.session.query(self.AllUsers).filter_by(user=username).one()

        query = self.session.query(self.UsersContacts, self.AllUsers.user). \
            filter_by(user=user.id). \
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        return [contact[1] for contact in query.all()]

    def users_list(self):
        query = self.session.query(
            self.AllUsers.user,
            self.AllUsers.last_conn,
        )
        return query.all()

    def active_users_list(self):
        query = self.session.query(
            self.AllUsers.user,
            self.ActiveUsers.ip,
            self.ActiveUsers.port,
            self.ActiveUsers.time_conn
        ).join(self.AllUsers)
        return query.all()

    def login_history(self, username=None):
        # Запрашиваем историю входа
        query = self.session.query(self.AllUsers.user,
                                   self.LoginHistory.last_conn,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        if username:
            query = query.filter(self.AllUsers.user == username)
        return query.all()

    def message_history(self):
        query = self.session.query(
            self.AllUsers.user,
            self.AllUsers.last_conn,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        return query.all()


if __name__ == '__main__':
    from pprint import pprint

    PATH = os.path.dirname(os.path.abspath(__file__))
    PATH = os.path.join(PATH, 'server_base.db3')

    # тестирование
    db = ServerDB(PATH)
    db.user_login('test_user1', '192.168.1.4', 65600)
    db.user_login('test_user2', '192.168.1.5', 65500)
    print('Должно быть 2 активных юзера. Проверяем: ', len(db.active_users_list()))
    pprint(db.active_users_list())

    print('=' * 50)
    print('Написали сообщение. Счетчики в истори должны увеличится')
    db.process_message('test_user1', 'test_user2')
    print('Message history')
    pprint(db.message_history())

    db.add_contact('test_user2', 'test_user1')
    db.add_contact('test_user1', 'test_user2')
    print('Контакты test_user1', db.get_contacts('test_user1'))
    db.remove_contact('test_user1', 'test_user2')
    print('Контакты test_user1 после удаления одного', db.get_contacts('test_user1'))

    print('*' * 50)
    db.user_logout('test_user1')
    print('Отключили. Должен остаться 1. Проверяем: ', len(db.active_users_list()))
    print('Общий список. Тут должны быть 2 наших test_user. Метод users_list')
    pprint(db.users_list())

    print('Отключили и второго. В общем списке без изменений')
    print(db.users_list())
    print('А вот активных должно стать Ноль')
    print(db.active_users_list())

    print('*' * 50)
    print('В истории наши тесты тоже засветились')
    print('история test_user1', db.login_history('test_user1'))
    print('история test_user2', db.login_history('test_user2'))
    print('история всех')
    pprint(db.login_history())

    user = db.session.query(db.AllUsers).filter_by(user='test_user1').first()
    print(user)
    if user:
        db.session.query(db.LoginHistory).filter_by(user=user.id).delete()
        db.session.query(db.ActiveUsers).filter_by(user=user.id).delete()
        db.session.query(db.UsersHistory).filter_by(user=user.id).delete()
        db.session.query(db.UsersContacts).filter_by(user=user.id).delete()
        db.session.query(db.AllUsers).filter_by(id=user.id).delete()
    user = db.session.query(db.AllUsers).filter_by(user='test_user2').first()
    if user:
        db.session.query(db.LoginHistory).filter_by(user=user.id).delete()
        db.session.query(db.ActiveUsers).filter_by(user=user.id).delete()
        db.session.query(db.UsersHistory).filter_by(user=user.id).delete()
        db.session.query(db.UsersContacts).filter_by(user=user.id).delete()
        db.session.query(db.AllUsers).filter_by(id=user.id).delete()
    db.session.commit()
