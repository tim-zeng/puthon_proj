# -*- coding:utf-8 -*-
# Author:      LiuSha
import os
import croniter
import importlib.util as import_module

from uuid import uuid1
from datetime import datetime
from dateutil.tz import tzlocal, gettz
from rq import get_current_job, worker
from rq_scheduler.utils import to_unix
from rq_scheduler.scheduler import Scheduler as rScheduler

from ecs import json

from flask_rq2 import RQ
from flask_rq2.job import FlaskJob


__all__ = ["run", "get_results", "uuid", "task_list", "InvalidFnError", "InvalidConfigError", "BaseTask"]


rq = RQ()


class InvalidFnError(Exception):

    def __init__(self, message=None):
        super().__init__(message or "Invalid function name")


class InvalidConfigError(Exception):

    def __init__(self, message=None):
        super().__init__(message or "Invalid config")


def uuid():
    return str(uuid1()).replace("-", "")


def absolute_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)))


def task_list():
    return [
        module_name[:-3]
        for module_name in os.listdir(absolute_path())
        if module_name != '__init__.py'
        if module_name.endswith('.py')
    ]


def get_module(fn):
    # invalidate_caches()
    spec = import_module.spec_from_file_location(fn, f"{absolute_path()}/{fn}.py")
    module = import_module.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def get_results(job_id, time=None):
    """
    :param str job_id: job id
    :param datetime time: when the task is not completed, time is None
    :return dict: result
    """
    job = rq.get_queue().fetch_job(job_id)
    if job.created_at and job.ended_at:
        time = f"{(job.ended_at - job.created_at).total_seconds():.2f}"

    description = job.description.lstrip("ecs.tasks.") if isinstance(job.description, str) else job.description
    return dict(result=job.result, status=job.status, time=time, description=description)


@rq.job(result_ttl=86400)
def run(mn, fn, *args, **kwargs):
    """
    :param mn: module name of task
    :param fn: function name of task
    :param args: function args of task
    :param kwargs: function kwargs of task
    :return: None
    """

    module = get_module(mn)
    klass = getattr(module, mn.capitalize())
    return klass.execute(fn, *args, **kwargs)


class BaseTask(object):

    failed = "failed"
    finished = "finished"
    suspend = "suspend"

    def __init__(self, job_id=None, cron=False):
        self.run = run
        self.uuid = uuid

        self.cron = cron
        self.task_log = None

        if self.cron:
            return

        if job_id:
            self.job = rq.get_queue().fetch_job(job_id)
        else:
            self.job = get_current_job()

    def get_job_data(self):
        description = self.job.description.lstrip("ecs.tasks.") \
            if isinstance(self.job.description, str) else self.job.description

        return {
            "id": self.job.id,
            "status": self.job.status,
            "meta": {"ttl": self.job.ttl, "timeout": self.job.timeout, "key": self.job.key.decode()},

            "time": None,
            "result": None,
            "description": description,
            "created_at": self.job.created_at,
            "started_at": self.job.started_at,
            "ended_at": None

        }

    def update_task_log(self, result=None, status=None):
        if status not in [self.finished, self.failed, self.suspend]:
            status = self.finished

        if not result:
            result = status

        if not self.cron and self.task_log:
            self.task_log.ended_at = datetime.utcnow()
            self.task_log.time = f"{(self.task_log.ended_at - self.job.created_at).total_seconds():.2f}"
            self.task_log.status = status

            if isinstance(result, (dict, list)):
                self.task_log.result = json.dumps(result)
            else:
                self.task_log.result = result

            self.task_log.save()
            self.job.set_status(status)

        return result


def cancel(job_id):
    jobs = rq.get_scheduler().get_jobs()
    for job in jobs:
        if job._id == job_id:
            # print('job:', job.__dict__)
            rq.get_scheduler().cancel(job)


class Scheduler(rScheduler):
    job_class = FlaskJob

    def __init__(self, *args, **kwargs):
        super(Scheduler, self).__init__(*args, **kwargs)

    @classmethod
    def get_next_scheduled_time(cls, cron_string):
        """Calculate the next scheduled time by creating a crontab object
            with a cron string"""

        itr = croniter.croniter(cron_string, datetime.now(tzlocal()))
        return itr.get_next(datetime).astimezone(gettz("UTC"))

    def schedule(self, scheduled_time, func, args=None, kwargs=None,
                 interval=None, repeat=None, result_ttl=None, ttl=None,
                 timeout=None, id=None, description=None, queue_name=None):
        """
        Schedule a job to be periodically executed, at a certain interval.
        """
        # Set result_ttl to -1 for periodic jobs, if result_ttl not specified
        if interval is not None and result_ttl is None:
            result_ttl = -1
        job = self._create_job(func, args=args, kwargs=kwargs, commit=False,
                               result_ttl=result_ttl, ttl=ttl, id=id or uuid(),
                               description=description, queue_name=queue_name,
                               timeout=timeout)

        scheduled_time = scheduled_time.replace(tzinfo=tzlocal())
        if interval is not None:
            job.meta['interval'] = int(interval)
        if repeat is not None:
            job.meta['repeat'] = int(repeat)
        if repeat and interval is None:
            raise ValueError("Can't repeat a job without interval argument")
        job.save()
        self.connection._zadd(self.scheduled_jobs_key,
                              to_unix(scheduled_time),
                              job.id)
        return job

    def cron(self, cron_string, func, args=None, kwargs=None, repeat=None,
             queue_name=None, id=None, timeout=None, description=None):
        """
        Schedule a cronjob
        """
        scheduled_time = self.get_next_scheduled_time(cron_string)

        # Set result_ttl to -1, as jobs scheduled via cron are periodic ones.
        # Otherwise the job would expire after 500 sec.
        job = self._create_job(func, args=args, kwargs=kwargs, commit=False,
                               result_ttl=-1, id=id or uuid(), queue_name=queue_name,
                               description=description, timeout=timeout)

        job.meta['cron_string'] = cron_string

        if repeat is not None:
            job.meta['repeat'] = int(repeat)

        job.save()

        self.connection._zadd(self.scheduled_jobs_key,
                              to_unix(scheduled_time),
                              job.id)
        return job

    def enqueue_job(self, job):
        """
        Move a scheduled job to a queue. In addition, it also does puts the job
        back into the scheduler if needed.
        """
        self.log.debug('Pushing {0} to {1}'.format(job.id, job.origin))

        interval = job.meta.get('interval', None)
        repeat = job.meta.get('repeat', None)
        cron_string = job.meta.get('cron_string', None)

        # If job is a repeated job, decrement counter
        if repeat:
            job.meta['repeat'] = int(repeat) - 1

        queue = self.get_queue_for_job(job)
        queue.enqueue_job(job)
        self.connection.zrem(self.scheduled_jobs_key, job.id)

        if interval:
            # If this is a repeat job and counter has reached 0, don't repeat
            if repeat is not None:
                if job.meta['repeat'] == 0:
                    return
            self.connection._zadd(self.scheduled_jobs_key,
                                  to_unix(datetime.utcnow()) + int(interval),
                                  job.id)
        elif cron_string:
            # If this is a repeat job and counter has reached 0, don't repeat
            if repeat is not None:
                if job.meta['repeat'] == 0:
                    return
            self.connection._zadd(self.scheduled_jobs_key,
                                  to_unix(self.get_next_scheduled_time(cron_string)),
                                  job.id)
