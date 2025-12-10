from flask_wtf import FlaskForm
from wtforms import SubmitField


class CsvvalidationForm(FlaskForm):
    submit = SubmitField("Save csvvalidation")
