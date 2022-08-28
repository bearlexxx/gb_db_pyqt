from setuptools import setup, find_packages

setup(name="ant_mess_server",
      version="0.1.0",
      description="Message Server",
      author="Ivan Ivanov",
      author_email="big-ant@inbox.ru",
      packages=find_packages(),
      install_requires=['PyQt5', 'sqlalchemy', 'pycryptodome', 'pycryptodomex'],
      scripts=['server/server_run']
      )
