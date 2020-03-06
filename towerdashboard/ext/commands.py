import click
from towerdashboard.ext.database import db
from towerdashboard.models import * # to be added later

def create_db():
    """Create database."""
    db.create_all()


def drop_db():
    """Clean database."""
    db.drop_all()

def populate_db():
    """Add data to db."""
    pass

def init_app(app):
    # add multiple commands in a bulk
    for command in [create_db, drop_db, populate_db]:
        app.cli.add_command(app.cli.command()(command))

