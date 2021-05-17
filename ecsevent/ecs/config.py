# -*- coding:utf-8 -*-
# Author:      Tim
import os
import sys
from multiprocessing import cpu_count


class AppConfig(object):
    #: Get the app root path
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    #: Python version
    PY_VERSION = '{0.major}{0.minor}'.format(sys.version_info)

    DEBUG = False

    #: Security
    #: generate a secret key with os.urandom(24)
    SECRET_KEY = '04b671e45f674d40aecf5af54fa910fd'

    #: The filename for the info and error logs. The logfiles are stored
    INFO_LOG = "info.log"
    ERROR_LOG = "error.log"
    ACCESS_LOG = "access.log"

    #: HTTP
    HTTP_WORKS = cpu_count() * 2 + 1

    #: default connection using db.default
    SQLALCHEMY_DATABASE_TMPL = 'mysql+pymysql://{USER}:{AUTH}@{HOST}:{PORT}/{NAME}?charset={CHARSET}'
    SQLALCHEMY_BINDS = {}
    # SQLALCHEMY_POOL_SIZE = 10

    #: This option will be removed as soon as Flask-SQLAlchemy removes it.
    #: | At the moment it is just used to suppress the super annoying warning
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    #: This will print all SQL statements
    SQLALCHEMY_ECHO = False
