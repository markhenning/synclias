from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_marshmallow import Marshmallow
from flask_login import LoginManager

class Base(DeclarativeBase):
  pass

## The actual init of these two, separated out for circular import redundancy fun
# db = SQLAlchemy(model_class=Base)
ma = Marshmallow()
login_manager = LoginManager()

