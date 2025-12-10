from app import db


class Csvvalidation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return f"Csvvalidation<{self.id}>"
