from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from app.modules.dataset.models import League


class AuthorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    affiliation = StringField("Affiliation")
    orcid = StringField("ORCID")
    gnd = StringField("GND")

    class Meta:
        csrf = False  # disable CSRF because is subform


class BasketModelForm(FlaskForm):
    csv_filename = StringField("CSV Filename", validators=[DataRequired()])
    title = StringField("Title", validators=[Optional()])
    desc = TextAreaField("Description", validators=[Optional()])
    league = SelectField(
        "League",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in League],
        validators=[Optional()],
    )
    tags = StringField("Tags (separated by commas)")
    version = StringField("CSV Version")

    class Meta:
        csrf = False  # disable CSRF because is subform

    def get_bmmetadata(self):
        return {
            "csv_filename": self.csv_filename.data,
            "title": self.title.data,
            "description": self.desc.data,
            "league": self.league.data,
            "tags": self.tags.data,
            "csv_version": self.version.data,
        }


class DataSetForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    desc = TextAreaField("Description", validators=[DataRequired()])
    league = SelectField(
        "League",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in League],
        validators=[DataRequired()],
    )
    tags = StringField("Tags (separated by commas)")
    basket_models = FieldList(FormField(BasketModelForm), min_entries=1)

    submit = SubmitField("Submit")

    def get_dsmetadata(self):
        league_converted = self.convert_league(self.league.data)

        return {
            "title": self.title.data,
            "description": self.desc.data,
            "league": league_converted,
            "tags": self.tags.data,
        }

    def convert_league(self, value):
        for league in League:
            if league.value == value:
                return league.name
        return "NONE"

    def get_basket_models(self):
        return [bm.get_basket_model() for bm in self.basket_models]
