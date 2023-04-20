'''Module for manging database operations.

'''
from datetime import datetime, timedelta
import os
import random
import getpass

from app import app, db, bcrypt, models


def create_prod():
    with app.app_context():
        db.create_all()

        admin = models.User(
            email=os.environ.get('EMAIL'),
            password=bcrypt.generate_password_hash(os.environ.get('PASSWORD')).decode('utf-8'),
            settings=models.UserSettings()
        )
        admin.save()


def create_dev():
    def random_binary_string(n):
        return ''.join(str(random.randint(0, 1)) for _ in range(n))

    with app.app_context():
        db.create_all()

        # User test data
        for i in range(1, 4):
            user = models.User(
                email='user{}@email.com'.format(i),
                password=bcrypt.generate_password_hash('password{}'.format(i)).decode('utf-8'),
                settings=models.UserSettings()
            )
            user.save()

        # PlugConfig test data
        for i in range(4, 8):
            plug = models.PlugConfig(
                name='{}-Pin Plug'.format(i),
                cure_profile=random_binary_string(i),
                horizontal_offset=round(random.uniform(0.1, 5), 2),
                vertical_offset=round(random.uniform(0.1, 5), 2),
                horizontal_gap=round(random.uniform(0.1, 5), 2),
                vertical_gap=round(random.uniform(0.1, 5), 2),
                slot_gap=round(random.uniform(0.1, 5), 2)
            )
            plug.save()

        # PlugJob test data
        for i in range(100):
            job = models.PlugJob(
                config_id=random.randint(1, 4),
                start_time=datetime.now() - timedelta(minutes=random.randint(20, 100))
            )
            job.end_time = job.start_time + timedelta(minutes=random.randint(20, 100))
            job.duration = round((job.end_time - job.start_time).total_seconds() / 60, 2)
            status_list = list(models.StatusEnum)
            status_list.remove(models.StatusEnum.started)
            job.status = random.choice(status_list)

            rand = random.random()
            if rand < 0.8:
                job.status = models.StatusEnum.finished
            elif rand < 0.9:
                job.status = models.StatusEnum.failed
            else:
                job.status = models.StatusEnum.stopped

            job.save()


def create_user(email, password):
    with app.app_context():
        user = models.User(
            email=email,
            password=bcrypt.generate_password_hash(password).decode('utf-8'),
            settings=models.UserSettings()
        )
        user.save()


def delete_all(confirm=False):
    if confirm:
        with app.app_context():
            db.drop_all()
    else:
        print(f'Please confirm deletion using boolean: delete_all(confirm=True)')
