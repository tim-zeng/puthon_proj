# -*- coding:utf-8 -*-
# Author:      Tim
from ecs import current_app
from ecs.tasks import InvalidFnError
from ecs.tasks.aliyun import Aliyun


class Cron(object):

    def __init__(self):
        self.aliyun_config = current_app.config['SRV'].get('ALIYUN')

    @property
    def aliyun_task(self):
        return Aliyun(self.aliyun_config, cron=True)

    def sync_aliyun_events(self):
        self.aliyun_task.sync_events()

    # @staticmethod
    # def test():
    #     print("testing")
    #     Aliyun.sync_events()

    @classmethod
    def execute(cls, fn, *args, **kwargs):
        """
        :param str fn: execute function name
        :return:
        """
        self = cls()
        if not (isinstance(fn, str) or not hasattr(self, fn)):
            raise InvalidFnError()

        getattr(self, fn)(*args, **kwargs)
