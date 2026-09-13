Flask-Migrate manages this directory. On a fresh checkout run:

flask --app run.py db init
flask --app run.py db migrate -m "initial schema"
flask --app run.py db upgrade

Do not hand-edit generated migration scripts without review.
