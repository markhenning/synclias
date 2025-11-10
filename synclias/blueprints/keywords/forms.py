from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, URLField, IntegerField, FormField, FieldList
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, url

class AddKeywordForm(FlaskForm):
    keyword = StringField('Add Keyword', validators=[DataRequired()])
    exact = BooleanField('Exact Match?')
    submit = SubmitField('AddKeyword')