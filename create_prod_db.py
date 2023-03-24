'''Module for creating the database from scratch.

This should only be run once during setup or in case of database
deletion. Run the file itself with `python create_db.py`.

'''
import os

from app import app, db, bcrypt, models


def create_db():
    with app.app_context():
        db_path = os.path.join('instance', os.environ.get('DATABASE_URL').split('///')[1])
        if os.path.exists(db_path):
            os.remove(db_path)

        db.create_all()

        # Create an admin user
        admin = models.User(
            email=os.environ.get('EMAIL', 'admin@email.com'),
            password=bcrypt.generate_password_hash(os.environ.get('PASSWORD', 'password')).decode('utf-8')
        )
        db.session.add(admin)
        db.session.commit()
        settings = models.UserSettings(user_id=admin.id)
        db.session.add(settings)
        db.session.commit()


if __name__ == '__main__':
    create_db()
