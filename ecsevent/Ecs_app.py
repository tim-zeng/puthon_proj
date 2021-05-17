# -*- coding:utf-8 -*-
# Author:      Tim
import os
import sys

from flask.cli import FlaskGroup

from ecs import create_app, tasks, cache
from ecs.config import AppConfig
from ecs import db
from ecs.tasks.aliyun import Aliyun
from ecs.tasks.cron import Cron

venv_path = os.environ.get("VENV_PATH", ".env")
print(venv_path)
#: windows
if os.name == 'nt':
    activate_this = os.path.join(AppConfig.BASE_DIR, venv_path, 'Scripts', 'activate_this.py')
else:
#: activate_this path
    activate_this = os.path.join(AppConfig.BASE_DIR, venv_path, 'bin', 'activate_this.py')

#: active virtualenv
with open(activate_this) as f:
    code = compile(f.read(), activate_this, 'exec')
    exec(code, dict(__file__=activate_this))

app = create_app(os.path.join(AppConfig.BASE_DIR, "config.yml"))
fg = FlaskGroup(app)


@app.shell_context_processor
def make_shell_context():
    model_dict = dict(app=app, db=db, cache=cache, tasks=tasks)
    
    return model_dict


@fg.command('recreate_db', help='Recreates a local database, You probably should not use this on production.')
def recreate_db():
    db.drop_all()
    db.create_all()
    db.session.commit()


@fg.command("run", help="run server")
def runserver():
    # Aliyun.sync_events()
    # tasks.run("cron", "sync_aliyun_events")
    # tasks.run.cron("* * * * *", "aliyun sync_events", mn="cron", fn="sync_aliyun_events")
    app.run(host=app.config["HOST"], port=app.config["PORT"], use_reloader=True)


if __name__ == '__main__':
    sys.exit(fg.main())
