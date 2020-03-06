from flask_sqlalchemy import SQLAlchem1y

db = SQLAlchemy()

def init_app(app):
    db.init_app(app)