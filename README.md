# A Web App for the Keynetics Robotics Project

Part of the 2022-2023 senior capstone design project by:
* Austin Kugler
* Taylor Martin
* Zach Preston

# Setup (Linux or WSL)
Create Environment:
```
git clone https://github.com/Trmart/Keynetics-Web-App.git
cd Keynetics-Web-App
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Create Database:
In the root directory, create a file named `.env` with the contents:
```
FLASK_SECRET_KEY='fredthebot'
DATABASE_URL='sqlite:///app.db'
APP_URL='http://127.0.0.1:5000'
EMAIL='youremail@email.com'
PASSWORD='yourpassword'
```
Then, run the below commands:
```
python3
>>> import manage_db
>>> manage_db.create_dev()
>>> exit()
```

Run Web App Locally:
```
python3 run.py
```

# Deploy to Heroku
* Create Heroku account and add a payment method.
* Subscribe to a Dyno plan
* Navigate to repo root directory.
* Install Heroku CLI and login:
```
curl https://cli-assets.heroku.com/install.sh | sh
heroku login
```
* Verify `requirements.txt` includes `psycopg2`. You may need to remove `psycopg2-binary==2.9.5` and redeploy if you encounter relevant errors.

* Verify `Profile` file is in repo root directory. If not, create it:
```
echo "web: gunicorn app:app" > Procfile
```
* Verify `requirements.txt` includes `gunicorn`, install it if not present.
```
pip install gunicorn
pip freeze > requirements.txt
```
* Verify all changes are added, committed, and pushed.
* Create and push the Heroku project:
```
heroku create
git push heroku main
```
* Create database:
```
heroku addons:create heroku-postgresql:mini
```
This will subscribe you to the Heroku Postgres Mini database add-on. Note: you may need to install psycopg2-binary using the Heroku CLI.
* Verify project's `DATABASE_URL`, `APP_URL`, `EMAIL`, `PASSWORD`, and `FLASK_SECRET_KEY` config vars are set to the correct values in the "Settings" tab of the Heroku dashboard. The `DATABASE_URL` value should match the output of:
```
heroku config:get DATABASE_URL
```
* Add dynos to the project:
```
heroku ps:scale web=1
```
* Create the database with an admin account:
```
heroku run python
>>> import manage_db
>>> manage_db.create_prod()
>>> exit()
```
```
* Open the hosted project:
```
heroku open
```
