# -*- coding:utf-8 -*-
import time
from datetime import datetime, timedelta
import json

from aliyunsdkactiontrail.request.v20171204 import LookupEventsRequest
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.profile import region_provider
from aliyunsdkcore.request import RpcRequest


class Aliapi(object):

    def __init__(self, ak=None, secret=None, region_id="cn-shenzhen"):
        """
        :param ak: access key
        :param secret: access secret
        :param region_id: only cn-shenzhen
        """
        self.region_id = region_id
        self.client = AcsClient(ak, secret, region_id)

        # region_provider.modify_point('BssOpenApi', 'cn-shenzhen', 'business.aliyuncs.com')

    def get_request_result(self, request):
        if not isinstance(request, RpcRequest):
            raise TypeError("request is not valid RpcRequest")

        try:
            response = self.client.do_action_with_exception(request)
        except ClientException as err:
            if "timed out" in err.message:
                time.sleep(2)

                response = self.client.do_action_with_exception(request)
            else:
                raise ValueError(err)
        except ServerException as err:
            raise ValueError(err)

        return response

    def get_events(self, start_time=None, end_time=None):
        events = []
        next_token = None

        def _request(max_results=50):
            request = LookupEventsRequest.LookupEventsRequest()
            request.set_query_params({
                "MaxResults": max_results,
                "StartTime": start_time if start_time else self.get_datetime(6),
                "EndTime": end_time if end_time else self.get_datetime()
            })

            if next_token:
                request.add_query_param("NextToken", next_token)

            return request

        while True:
            result = json.loads(self.get_request_result(_request()))
            events += result["Events"]

            next_token = result.get("NextToken")
            if isinstance(next_token, str) and next_token == str(len(events)):
                continue

            break

        return events

    @classmethod
    def get_datetime(cls, offset=None):
        now = datetime.utcnow()
        if isinstance(offset, int):
            now = now - timedelta(minutes=offset)

        return now.strftime('%Y-%m-%dT%H:%M:%SZ')
