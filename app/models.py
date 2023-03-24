'''Module defining database tables.

Uses `Flask-SQLAlchemy`_ to define model classes which represent tables
in a database and their relationships.

.. _Flask-SQLAlchemy
    https://flask-sqlalchemy.palletsprojects.com/en/2.x/

'''
from flask_login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property

from datetime import datetime
from enum import Enum
import uuid

from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Table():

    @classmethod
    def get_all(cls):
        return cls.query.all()

    @classmethod
    def get_by_id(cls, id):
        return cls.query.get(id)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class User(db.Model, UserMixin, Table):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)
    settings = db.relationship('UserSettings', backref='user', uselist=False)

    def __init__(self, email, password, settings):
        self.email = email
        self.password = password
        self.settings = settings

    def __repr__(self):
        return f'User(id={self.id}, email={self.email})'

    def json(self):
        return {
            'id': self.id,
            'email': self.email
        }

    @classmethod
    def get_by_email(cls, email):
        return cls.query.filter_by(email=email).first()


class SortByEnum(Enum):
    id = 'id'
    name = 'name'
    status = 'status'
    start_time = 'start_time'
    end_time = 'end_time'
    duration = 'duration'


class UserSettings(db.Model, Table):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sort_by = db.Column(db.Enum(SortByEnum), nullable=False)
    only_show_active = db.Column(db.Boolean, nullable=False)

    def __init__(self, sort_by=SortByEnum.start_time, only_show_active=True):
        self.sort_by = sort_by
        self.only_show_active = only_show_active

    def __repr__(self):
        return f'UserSettings(id={self.id}, user_id={self.user_id}, sort_by={self.sort_by})'

    def json(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'sort_by': self.sort_by
        }

    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).first()

    def get_sort_by(self):
        return self.sort_by.value


class PlugConfig(db.Model, Table):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True)
    cure_profile = db.Column(db.String(32), nullable=False)
    horizontal_offset = db.Column(db.Float, nullable=False)
    vertical_offset = db.Column(db.Float, nullable=False)
    horizontal_gap = db.Column(db.Float, nullable=False)
    vertical_gap = db.Column(db.Float, nullable=False)
    slot_gap = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(256), nullable=True)
    is_removed = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, name, cure_profile, horizontal_offset, vertical_offset, horizontal_gap, vertical_gap, slot_gap, notes=''):
        self.name = name
        self.cure_profile = cure_profile
        self.horizontal_offset = horizontal_offset
        self.vertical_offset = vertical_offset
        self.horizontal_gap = horizontal_gap
        self.vertical_gap = vertical_gap
        self.slot_gap = slot_gap
        self.notes = notes

    def __repr__(self):
        return f'PlugConfig(id={self.id}, name={self.name}, cure_profile={self.cure_profile})'

    def json(self):
        return {
            'id': self.id,
            'name': self.name,
            'cure_profile': self.cure_profile,
            'horizontal_offset': self.horizontal_offset,
            'vertical_offset': self.vertical_offset,
            'horizontal_gap': self.horizontal_gap,
            'vertical_gap': self.vertical_gap,
            'slot_gap': self.slot_gap,
            'notes': self.notes,
            'is_removed': self.is_removed
        }

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    @classmethod
    def query_not_removed(cls):
        return cls.query.filter_by(is_removed=False).order_by(cls.name)

    def remove(self):
        self.is_removed = True
        db.session.commit()


class StatusEnum(Enum):
    started = 'started'
    stopped = 'stopped'
    finished = 'finished'
    failed = 'failed'


class PlugJob(db.Model, Table):
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('plug_config.id'), nullable=False)
    config = db.relationship('PlugConfig', backref=db.backref('jobs', lazy=True))
    start_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Enum(StatusEnum), nullable=False)
    notes = db.Column(db.String(256), nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Float, nullable=True)

    def __init__(self, config_id, start_time, status=StatusEnum.started, notes=''):
        self.config_id = config_id
        self.start_time = start_time
        self.status = status
        self.notes = notes

    def __repr__(self):
        return f'PlugJob(id={self.id}, config_id={self.config_id}, status={self.status})'

    def is_active(self):
        return self.status == StatusEnum.started

    @hybrid_property
    def query_is_active(self):
        return self.status == StatusEnum.started

    def json(self):
        return {
            'id': self.id,
            'config_id': self.config_id,
            'status': self.status.value,
            'start_time': self.start_time.timestamp() if self.start_time else None,
            'end_time': self.end_time,
            'duration': self.duration,
            'notes': self.notes,
            'config': self.config.json()
        }

    @classmethod
    def get_by_config(cls, config_id):
        return cls.query.filter_by(config_id=config_id).all()

    @classmethod
    def query_active(cls):
        return cls.query.filter_by(status=StatusEnum.started)

    @classmethod
    def get_active(cls):
        return cls.query_active().all()

    @classmethod
    def query_inactive(cls):
        return cls.query.filter(cls.status != StatusEnum.started)

    @classmethod
    def get_inactive(cls):
        return cls.query_inactive().all()

    @classmethod
    def get_started(cls):
        return cls.query.filter_by(status=StatusEnum.started).all()

    @classmethod
    def get_stopped(cls):
        return cls.query.filter_by(status=StatusEnum.stopped).all()

    @classmethod
    def get_finished(cls):
        return cls.query.filter_by(status=StatusEnum.finished).all()

    @classmethod
    def get_failed(cls):
        return cls.query.filter_by(status=StatusEnum.failed).all()

    def stop(self):
        self.status = StatusEnum.stopped
        self.end()

    def end(self):
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        db.session.commit()


class APIKey(db.Model, Table):
    # __table_args__ = (db.UniqueConstraint('user_id', name='user_id'),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('api_keys', lazy=True))
    key = db.Column(db.String(64), nullable=False, unique=True)

    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id
        self.key = str(uuid.uuid4())

    def __repr__(self):
        return f'APIKey(id={self.id}, name={self.name}, user_id={self.user_id})'

    def json(self):
        return {
            'id': self.id,
            'name': self.name,
            'key': self.key,
            'user_id': self.user_id
        }

    @classmethod
    def get_by_key(cls, key):
        return cls.query.filter_by(key=key).first()

    @classmethod
    def get_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()
