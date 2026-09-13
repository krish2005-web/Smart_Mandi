import os
os.environ['DATABASE_URL']='sqlite+pysqlite:///:memory:'
os.environ['DEMO_MODE']='true'
import pytest
from app import create_app
from app.extensions import db

@pytest.fixture()
def app():
    a=create_app(); a.config.update(TESTING=True,SQLALCHEMY_DATABASE_URI='sqlite+pysqlite:///:memory:')
    with a.app_context(): db.create_all(); yield a; db.drop_all()
@pytest.fixture()
def client(app): return app.test_client()

def test_states_endpoint(client):
    r=client.get('/api/states'); assert r.status_code==200 and r.json['success'] is True

def test_login_requires_credentials(client):
    r=client.post('/api/auth/login',json={'identifier':'x','password':'x'}); assert r.status_code==401
