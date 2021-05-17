# -*- coding:utf-8 -*-
import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import JSONType

__all__ = ["AliEvent", "db"]

db = SQLAlchemy()


class AliEvent(db.Model):
    __tablename__ = "ali_event"

    #: 事件ID，由 ActionTrail 服务为每个操作事件所产生的一个GUID。
    id = db.Column(db.String(64), primary_key=True)
    #: API 操作名称，比如 Ecs 的 StopInstance 。
    name = db.Column(db.String(64))
    #: 处理 API 请求的服务端，比如 ram.aliyuncs.com 。
    source = db.Column(db.String(255))
    #: API 请求的发生时间 - UTC
    request_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    #: 事件类型，如 ApiCall（控制台或 API 操作）, ConsoleSignin（用户登录）。
    type = db.Column(db.String(255))
    #: ActionTrail 事件格式的版本。
    version = db.Column(db.String(255))
    #: optional | 如果云服务处理 API 请求时发生了错误，这里记录了相应的错误码，比如 NoPermission。·
    err_code = db.Column(db.String(255), default=-1)
    #: optional | 如果云服务处理API请求时发生了错误，这里记录了相应的错误消息，比如 You are not authorized.
    err_msg = db.Column(db.Text, default="")
    #: 云服务处理 API 请求时所产生的消息请求 ID 。
    request_id = db.Column(db.String(64), default="")
    #: optional | 用户 API 请求的输入参数
    request_param = db.Column(JSONType, default={})
    #: 云服务名称，如 Ecs, Rds, Ram。
    service_name = db.Column(db.String(64))
    #: 发送API请求的源IP地址。如果API请求是由用户通过控制台操作触发，
    #: -> 那么这里记录的是用户浏览器端的IP地址，而不是控制台Web服务器的IP地址。
    source_ip = db.Column(db.CHAR(64))
    #: 发送 API 请求的客户端代理标识，比如控制台为 AliyunConsole ，SDK 为 aliyuncli/2.0.6 。
    user_agent = db.Column(db.CHAR(255))
    identity = db.Column(JSONType)

    created_by = db.Column(db.CHAR(128), nullable=False, default="unknow")

    @classmethod
    def get(cls):
        events = cls.query.all()
        return events

    @classmethod
    def get_id(cls):
        event_ids = cls.query.with_entities(cls.id).all()
        return event_ids

    @classmethod
    def add(cls, data):
        event = cls(**data)
        event.save()

        return event

    def save(self):
        """
        save model
        """
        db.session.add(self)
        db.session.commit()
        return self
