#!/usr/bin/env python
from flask_script import Manager
from app.application import app
from flask_migrate import MigrateCommand

manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()