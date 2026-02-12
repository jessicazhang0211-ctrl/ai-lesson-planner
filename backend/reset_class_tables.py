from app import create_app
from app.extensions import db
from sqlalchemy import inspect, text

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    if 'class_students' in inspector.get_table_names() or 'classes' in inspector.get_table_names():
        print('Dropping tables if exist: classes, class_students')
        with db.engine.connect() as conn:
            conn.execute(text('DROP TABLE IF EXISTS class_students'))
            conn.execute(text('DROP TABLE IF EXISTS classes'))
    print('Creating all tables')
    db.create_all()
    print('Done')
