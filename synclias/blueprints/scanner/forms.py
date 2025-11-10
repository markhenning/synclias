from flask_wtf import FlaskForm, Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, URLField, IntegerField, FormField, FieldList
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, url
from wtforms.widgets import PasswordInput
import sqlalchemy as sa
from synclias import db
from synclias.models import User


class ScannerForm(FlaskForm):
    target = StringField('URL', validators=[DataRequired()])
    safe_scan = BooleanField('Safe Scan Mode (href and img only)', default="checked") # type: ignore - Docs say I can put anything in here that isn't 0
    submit = SubmitField('ScanURL')
