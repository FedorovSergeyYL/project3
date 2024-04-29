from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, FileField
from wtforms.fields.simple import EmailField
from wtforms.validators import DataRequired


class ProfileForm(FlaskForm):

    email = EmailField('Почта', validators=[DataRequired()])
    name = StringField('Имя пользователя', validators=[DataRequired()])
    photo = StringField('Аватар пользователя')
    about = TextAreaField("Информация о себе")
    submit = SubmitField('Сохранить изменения')