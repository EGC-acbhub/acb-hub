from datetime import datetime

from app import db


class FakeDeposition(db.Model):
    __tablename__ = 'fake_deposition'
    id = db.Column(db.Integer, primary_key=True)
    conceptrecid = db.Column(db.Integer, unique=True, nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    upload_type = db.Column(db.String(50), default='dataset')
    creators = db.Column(db.Text)  # JSON string
    keywords = db.Column(db.Text)  # JSON string
    access_right = db.Column(db.String(20), default='open')
    license = db.Column(db.String(50), default='CC-BY-4.0')
    doi = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(20), default='unsubmitted')  # unsubmitted, submitted, done
    created = db.Column(db.DateTime, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to files
    files = db.relationship('FakeFile', backref='deposition', lazy=True, cascade='all, delete')

    def to_dict(self):
        return {
            'id': self.id,
            'conceptrecid': self.conceptrecid,
            'doi': self.doi,
            'metadata': {
                'title': self.title,
                'description': self.description,
                'upload_type': self.upload_type,
                'creators': self.creators,
                'keywords': self.keywords,
                'access_right': self.access_right,
                'license': self.license,
            },
            'files': [],  # Will be populated by service layer
            'state': self.state,
            'created': self.created.isoformat() if self.created else None,
            'modified': self.modified.isoformat() if self.modified else None,
        }

    def __repr__(self):
        return f'FakeDeposition<{self.id}, state={self.state}>'


class FakeFile(db.Model):
    __tablename__ = 'fake_file'
    id = db.Column(db.Integer, primary_key=True)
    deposition_id = db.Column(db.Integer, db.ForeignKey('fake_deposition.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filesize = db.Column(db.Integer, nullable=False)
    checksum = db.Column(db.String(100), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'filesize': self.filesize,
            'checksum': self.checksum,
        }

    def __repr__(self):
        return f'FakeFile<{self.filename}, size={self.filesize}>'


class Fakenodo(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return f'Fakenodo<{self.id}>'
