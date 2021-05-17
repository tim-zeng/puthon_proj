# -*- coding:utf-8 -*-
# Author:      Tim
import os
import sys
import yaml
from flask_caching import Cache
from flask_migrate import Migrate
from datetime import date, datetime, timedelta
from decimal import Decimal
from ipaddress import IPv4Address
from sqlalchemy.ext.associationproxy import _AssociationList

from ecs.event_model import db
from flask import g, json, request as current_request, Response, current_app, Flask, Config
from ecs import tasks

__all__ = ["cache", "create_app", "current_app", "g", "db", "current_request"]

from ecs.tasks import rq

cache = Cache()


def create_app(config_path=None):
    """ Create Flask App """
    app = App(__name__, static_folder="static", template_folder="static")

    init_config(app, config_path)
    init_database(app)

    #: init cache
    cache.init_app(app)
    init_rq(app)

    return app


def init_config(app, config_path):
    app.config.from_object('ecs.config.AppConfig')
    config_path = type(config_path) is str and os.path.abspath(config_path)

    if os.path.exists(config_path):
        app.config.from_yaml(config_path)
        app.config["CONFIG_PATH"] = config_path
        app.config["STATIC_PATH"] = os.path.join(app.config["BASE_DIR"], "app", "static")

        tmpl = app.config["SQLALCHEMY_DATABASE_TMPL"]
        app.config["SQLALCHEMY_DATABASE_URI"] = tmpl.format(**app.config.get("DB")["DEFAULT"])
        app.config["SQLALCHEMY_BINDS"] = {
            {name: tmpl.format(**conf)}
            for name, conf in app.config.get("DB").items() if name != "DEFAULT"
        }

        if not app.debug:
            app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

    sys.path.insert(0, app.config["BASE_DIR"])


def init_database(app):
    db.init_app(app)
    db.app = app

    Migrate(app, db)


def init_rq(app):
    tasks.rq.init_app(app)

    # default_queue = rq.get_queue()
    # easy_job = default_queue.enqueue(tasks.run, args=(1, 2))

    # default_worker = rq.get_worker()
    # default_worker.work(burst=True)
    #
    # scheduler = rq.get_scheduler(interval=10)
    # scheduler.run()
    tasks.run.cron("* * * * *", "aliyun sync_events", mn="cron", fn="sync_aliyun_events")
    # tasks.run.schedule(timedelta(seconds=1), repeat=None, interval=20, mn="cron", fn="sync_aliyun_events")


class LoadAppConfig(Config):
    """Extension of standard Flask app with custom Config class."""

    def from_yaml(self, config_file):
        """config.yml enhanced with a `from_yaml` method."""
        with open(config_file) as f:
            configs = yaml.load(f)

        for key in configs.get("APP").keys():
            if key.isupper():
                self[key] = configs["APP"][key]

        self["DB"] = configs["DB"]
        self["SRV"] = configs.get("SRV", {})


class AppJSONEncoder(json.JSONEncoder):
    _needs_to_process = (set, datetime, timedelta, date, Decimal, _AssociationList, IPv4Address)

    def default(self, obj):
        if type(obj) in self._needs_to_process:
            if isinstance(obj, datetime):
                return obj.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(obj, timedelta):
                return obj.seconds
            if isinstance(obj, date):
                return obj.strftime("%Y-%m-%d")
            if isinstance(obj, Decimal):
                return int(obj)
            if isinstance(obj, (_AssociationList, set)):
                return list(obj)
            if isinstance(obj, IPv4Address):
                return str(obj)
        elif callable(obj):
            return str(obj)

        #: Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class AppResponse(Response):
    """
    Extend flask.Response with support for list/dict conversion to JSON,
    and set Response Status Code.
    """
    charset = 'utf-8'
    default_status = 200

    def __init__(self, content=None, *args, **kargs):
        # print('content....', json.dumps(content, indent=2))
        if isinstance(content, (list, dict)):
            kargs['mimetype'] = 'application/json'
            if isinstance(content, dict) and content.get('status'):
                kargs['status'] = content['status']

            content = self.to_json(content)

        super(Response, self).__init__(content, *args, **kargs)

    @staticmethod
    def to_json(content):
        """Converts content to json while respecting config.yml options."""
        indent = None
        separators = (',', ':')

        if current_app.config['JSONIFY_PRETTYPRINT_REGULAR'] and not current_request.is_xhr:
            indent = 4
            separators = (', ', ': ')

        return json.dumps(content, indent=indent, separators=separators, cls=AppJSONEncoder)

    @classmethod
    def force_type(cls, response, environ=None):
        """Override with support for list/dict."""
        if isinstance(response, (list, dict)):
            return cls(response)
        else:
            return super(Response, cls).force_type(response, environ)


class App(Flask):
    """Extension of standard Flask app with custom response class."""
    response_class = AppResponse

    def make_config(self, instance_relative=False):
        root_path = self.root_path
        if instance_relative:
            root_path = self.instance_path
        return LoadAppConfig(root_path, self.default_config)
