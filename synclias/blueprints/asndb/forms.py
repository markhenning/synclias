from flask_wtf import FlaskForm, Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, URLField, IntegerField, FormField, FieldList
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, url
from wtforms.widgets import PasswordInput
import sqlalchemy as sa
#from synclias import db
from synclias.models import User
from flask import current_app

class AddASNForm(FlaskForm):
    asn = IntegerField('ASN', validators=[DataRequired()])
    comment = StringField('Comment')
    submitasn = SubmitField('AddASN')

class LookupASNForm(FlaskForm):
    target = StringField('Domain', validators=[DataRequired()])
    submitlookup = SubmitField('LookupASN')