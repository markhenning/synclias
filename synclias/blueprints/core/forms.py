from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, IntegerField, FormField, FieldList
from wtforms.validators import DataRequired
from wtforms.widgets import PasswordInput
import sqlalchemy as sa
from synclias import db
from synclias.models import User


class RouterForm(FlaskForm):
    hostname = StringField('Hostname', validators=[DataRequired()])
    apikey = StringField('API Key', validators=[DataRequired()])
    apisecret = StringField('API Secret', widget=PasswordInput(hide_value=False))
    alias = StringField('Alias', validators=[DataRequired()])
    ipv6 = BooleanField('IPv6 Enabled')
    alias_ipv6 = StringField('IPv6 Alias')
    Submit = SubmitField('Update Router')

class NameServerEntry(FlaskForm):
    id = IntegerField('Internal ID')
    hostname = StringField('Hostname', validators=[DataRequired()])
    type = StringField('NS Type', validators=[DataRequired()])
    port = IntegerField('Mgmt Port')
    https = BooleanField('HTTPS')
    verifytls = BooleanField('Verify TLS')
    token = StringField('Token', widget=PasswordInput(hide_value=False))

class NameServersForm(FlaskForm):
    entries = FieldList(FormField(NameServerEntry), min_entries=1)

