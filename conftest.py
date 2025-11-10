import pytest
from synclias import create_app
from synclias.models import User, Prefs
from flask import session
from synclias import db
import os
from flask_bootstrap import Bootstrap5

@pytest.fixture(scope='module')
def test_client():
    # Set the Testing configuration prior to creating the Flask application
    os.environ['CONFIG_TYPE'] = 'TestingConfig'
    flask_app = create_app()

    # Create a test client using the Flask application configured for testing
    with flask_app.test_client() as testing_client:
        # Establish an application context
        with flask_app.app_context():
            yield testing_client  # this is where the testing happens!

@pytest.fixture(scope='function')
def session(db, request):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)

    db.session = session

    def teardown():
        transaction.rollback()
        connection.close()
        session.remove()

    request.addfina

@pytest.fixture(scope='module')
def init_database(test_client):
    # Create the database and the database table
    db.create_all()
    

    # Insert user data
    users = db.session.query(User).all()
    for user in users:
        db.session.delete(user)
    db.session.commit()

    default_user = User(username='admin',email='adminis@local',role='admin',password_hash='scrypt:32768:8:1$KVhxmYcLNd9q3TuM$bdf854007b4c84c9182ee74e4336f4c620d940830b2405d36071ecf6c52a424a287d066f328557d5a3773e0893f5e3ab1fac80335d4adf8f1fd8768f9a07138a')

    db.session.add(default_user)
    
    # Commit the changes for the users
    db.session.commit()

    prefs=db.session.query(Prefs).all()
    for pref in prefs:
        db.session.delete(pref)
    db.session.commit()

    prefs = Prefs(autosync=1,sync_every=60,autoasndb=1,asndb_every=7,purgedns=1,user_agent="")

    db.session.add(prefs)
    # Commit the changes for the books
    db.session.commit()

    yield  # this is where the testing happens!

    #db.drop_all()


@pytest.fixture(scope='function')
def log_in_default_user(test_client):
    test_client.post('/auth/login',
                     data={'password': 'password'})

    yield  # this is where the testing happens!

    ##test_client.get('/logout')
