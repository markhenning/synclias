import os
from str_to_bool import str_to_bool

#Celery
from celery import Celery
from celery import Task
## Flask modules
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap5
from flask_migrate import Migrate

from werkzeug.debug import DebuggedApplication
from flask_debugtoolbar import DebugToolbarExtension

from synclias.extensions import ma
from synclias.extensions import login_manager

#from synclias.extensions import csrf
#from .api import api  ## Left in, but never used, will be in V1

from sqlalchemy.orm import DeclarativeBase

toolbar = DebugToolbarExtension()

## Needed to allow for transparent encryption setup
class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

def create_celery_app(app=None):
    """
    Create a new Celery object and tie together the Celery config to the app's
    config. Wrap all tasks in the context of the application.
    """
    app = app or create_app()

    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context(): # type: ignore
                return self.run(*args, **kwargs)

    celery = Celery(app.import_name, task_cls=FlaskTask)
    celery.conf.update(app.config.get("CELERY_CONFIG", {}))
    celery.set_default()
    app.extensions["celery"] = celery

    return celery

#def create_app(settings_override=None,test_config=False):
def create_app(settings_override=None):
    """
    Create a Flask application using the app factory pattern.

    """
    app = Flask(__name__, static_folder="static", static_url_path="")

    ## Config load
    # Pull in what type of config to load ....
    config_type = os.getenv('CONFIG_TYPE', default='DevelopmentConfig')

    # ....and load it
    config_loader = 'config.settings.' + config_type
    app.config.from_object(config_loader)

    if settings_override:
        app.config.update(settings_override)

    ## Easy way to see if I've accidentally left in Dev/Testing mode
    app.logger.info(f"INFO: Running: {config_type}")

    ## DB Setup
    db.init_app(app)
    from . import models
    with app.app_context():
        db.create_all()
        ## Commit here to help avoid "partially initiated"
        db.session.commit()
        ## Marshmallow init, ma imported from 'extensions.py'
        ma.init_app(app)
        ## API Init
        ##api.init_app(app) ## Edited out for now, will be in V1

    migrate = Migrate(app, db)

    ### Login Manager Setup
    login_manager.init_app(app) # Login manager init, imported from 'extensions.py'
    login_manager.login_message = ''

    ## Need login to exist before view imports
    from synclias.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    ## Extensions
    extensions(app)

    ## Blueprints
    from synclias.blueprints.technitium.views import technitium
    from synclias.blueprints.standard_ns.views import standard_ns
    from synclias.blueprints.asndb.views import asndb
    from synclias.blueprints.sites.views import sites
    from synclias.blueprints.core.views import core
    from synclias.blueprints.scanner.views import scanner
    from synclias.blueprints.opnsense.views import opnsense
    from synclias.blueprints.syncer.views import syncer
    from synclias.blueprints.auth.views import auth
    from synclias.blueprints.scheduler.views import scheduler
    from synclias.blueprints.keywords.views import keywords
    from synclias.blueprints.history.views import history
    from synclias.blueprints.ip_history.views import ip_history
    

    app.register_blueprint(core)
    app.register_blueprint(technitium, url_prefix="/technitium")
    app.register_blueprint(standard_ns, url_prefix="/standard_ns")
    app.register_blueprint(scanner, url_prefix="/scanner")
    app.register_blueprint(opnsense, url_prefix="/opnsense")
    app.register_blueprint(syncer,url_prefix="/syncer")
    app.register_blueprint(scheduler, url_prefix="/scheduler")
    app.register_blueprint(sites, url_prefix="/site")
    app.register_blueprint(keywords,url_prefix="/keyword")
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(asndb, url_prefix="/asn")
    app.register_blueprint(history, url_prefix="/history")
    app.register_blueprint(ip_history, url_prefix="/ip_history")

    ## Need views to exist before applying the login manager view
    login_manager.login_view = 'auth.login' # type: ignore

    # shell context for flask cli
    @app.shell_context_processor
    def ctx():
        return {"app": app, "db": db}
    
    ## Admin reset check
    clear_admin = str_to_bool(os.getenv('CLEAR_ADMIN', default="False"))
    if clear_admin:
        with app.app_context():
            admin_user = User.query.first()
            if admin_user is not None:
                db.session.delete(admin_user)
                db.session.commit()

    return app


def extensions(app):
    Bootstrap5(app)
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    #if app.config_type == 'DevelopmentConfig':
    #    toolbar.init_app(app)
    
    ## Deliberately commented out, due for v1
    #api.init_app(app)

    return None


def middleware(app):

    # Enable the Flask interactive debugger in the brower for development.
    if app.debug:
        app.wsgi_app = DebuggedApplication(app.wsgi_app, evalex=True)

    return None

celery_app = create_celery_app()
