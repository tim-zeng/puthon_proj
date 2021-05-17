# -*- coding:utf-8 -*-
import json

from aliyunsdkactiontrail.request.v20171204 import LookupEventsRequest
from aliyunsdkcore import client
from aniso8601 import parse_datetime
from dateutil import tz
from ecs.tasks import BaseTask, InvalidConfigError
from ali import Aliapi
from ecs.event_model import AliEvent


class Aliyun(BaseTask):

    def __init__(self, config, cron=False):
        if not config:
            raise InvalidConfigError()
        self.ak = config["AK"]
        self.secret = config["SECRET"]
        self.api = self.get_api()
        self.cron = cron
        super(Aliyun, self).__init__(cron=self.cron)

    @classmethod
    def parse_time(cls, _time):
        return parse_datetime(_time).astimezone(tz.tzlocal())

    @classmethod
    def conv_event(cls, i):
        event = {
            "id": i["eventId"], "name": i["eventName"],
            "type": i["eventType"], "version": i["eventVersion"], "request_id": i["requestId"],
            "service_name": i["serviceName"], "source_ip": i["sourceIpAddress"], "identity": i["userIdentity"],
            "request_time": cls.parse_time(i["eventTime"])
        }

        if i.get("errorCode"):
            event["err_code"] = i["errorCode"]
        if i.get("errorMessage"):
            event["err_msg"] = i["errorMessage"]
        if i.get("requestParameters"):
            event["request_param"] = i["requestParameters"]
        if i.get("userAgent"):
            event["user_agent"] = i["userAgent"]
        if i["userIdentity"].get("userName"):
            event["created_by"] = i["userIdentity"]["userName"]
        if i.get("eventSource"):
            event["source"] = i["eventSource"]

        return event

    def get_api(self):
        return Aliapi(self.ak, self.secret)

    def db_events_put(self, start_time=None, end_time=None):
        events = [self.conv_event(event) for event in self.api.get_events(start_time, end_time)]

        for _event in events:
            AliEvent.add(_event)
        return events

    @staticmethod
    def get_events():
        clt = client.AcsClient('', '', 'cn-shenzhen')

        request = LookupEventsRequest.LookupEventsRequest()
        response = clt.do_action_with_exception(request)
        return response

    @staticmethod
    def sync_events():
        aliyun = []
        event_ids = []
        response = Aliyun.get_events()
        result = json.loads(response)
        # events += result["Events"]
        results = result["Events"]
        # print(results)
        for event in results:
            # print(event)
            e = Aliyun.conv_event(event)
            aliyun.append(e)
        print(len(aliyun))
        all_event_id = AliEvent.get_id()
        for i in range(len(all_event_id)):
            _id = str(all_event_id[i][0])
            event_ids.append(_id)
        print(len(event_ids))
        for _event in aliyun:
            if "user_agent" in _event.keys():
                if len(_event["user_agent"]) > 255 or _event["id"] in event_ids:
                    continue
                res = AliEvent.add(_event)
