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

PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'server_base.db3')


class ServerDB:
    Base = declarative_base()

    class AllUsers(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        login = Column(String, unique=True)
        last_conn = Column(DateTime)

        def __init__(self, login):
            self.login = login
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

    def __init__(self):
        # self.engine = create_engine('sqlite:///server_base.db3', echo=False, pool_recycle=7200)

        db_path = os.path.join("db", "server_base.db3")
        self.engine = create_engine('sqlite:///' + PATH, echo=False, pool_recycle=7200)

        self.Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username, ip_address, port):
        rez = self.session.query(self.AllUsers).filter_by(login=username)
        if rez.count():
            user = rez.first()
            user.last_conn = datetime.datetime.now()
        else:
            user = self.AllUsers(username)
            self.session.add(user)

        self.session.commit()

        new_active_user = self.ActiveUsers(user.id, ip_address, port)
        self.session.add(new_active_user)

        history = self.LoginHistory(user.id, ip_address, port)
        self.session.add(history)

        self.session.commit()

    def user_logout(self, username):
        user = self.session.query(self.AllUsers).filter_by(login=username).first()

        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()

        self.session.commit()

    def users_list(self):
        query = self.session.query(
            self.AllUsers.login,
            self.AllUsers.last_conn,
        )
        return query.all()

    def active_users_list(self):
        query = self.session.query(
            self.AllUsers.login,
            self.ActiveUsers.ip,
            self.ActiveUsers.port,
            self.ActiveUsers.time_conn
        ).join(self.AllUsers)
        return query.all()

    def login_history(self, username=None):
        query = self.session.query(self.AllUsers.login,
                                   self.LoginHistory.last_conn,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        if username:
            query = query.filter(self.AllUsers.login == username)
        return query.all()


if __name__ == '__main__':
    # тестирование
    db = ServerDB()
    db.user_login('test_user1', '192.168.1.4', 65600)
    db.user_login('test_user2', '192.168.1.5', 65500)
    print(len(db.active_users_list()))
    # print(db.active_users_list())

    db.user_logout('test_user1')
    print(len(db.active_users_list()))
    print(db.users_list())

    db.user_logout('test_user2')
    print(db.users_list())
    print(db.active_users_list())

    print(db.login_history('test_user1'))
    print(db.login_history('test_user2'))
    print(db.login_history())

    user = db.session.query(db.AllUsers).filter_by(login='test_user1').first()
    print(user)
    if user:
        db.session.query(db.LoginHistory).filter_by(user=user.id).delete()
        db.session.query(db.ActiveUsers).filter_by(user=user.id).delete()
        db.session.query(db.AllUsers).filter_by(id=user.id).delete()
    user = db.session.query(db.AllUsers).filter_by(login='test_user2').first()
    if user:
        db.session.query(db.LoginHistory).filter_by(user=user.id).delete()
        db.session.query(db.ActiveUsers).filter_by(user=user.id).delete()
        db.session.query(db.AllUsers).filter_by(id=user.id).delete()
    db.session.commit()
