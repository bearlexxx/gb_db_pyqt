from setuptools import setup, find_packages

setup(name="ant_mess_client",
      version="0.1.0",
      description="Message Client",
      author="Ivan Ivanov",
      author_email="big-ant@inbox.ru",
      packages=find_packages(),
      install_requires=['PyQt5', 'sqlalchemy', 'pycryptodome', 'pycryptodomex']
      )
