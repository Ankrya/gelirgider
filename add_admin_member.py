import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from src.models.finance_models import db
from src.models.member import Member

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:3184156@localhost:3306/mydb"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.session.rollback()
    if not Member.query.filter_by(username="admin").first():
        admin = Member(username="admin", email="admin@example.com", password_hash="pass")
        db.session.add(admin)
        db.session.commit()
        print("Admin kullanıcısı başarıyla eklendi!")
    else:
        print("Admin kullanıcısı zaten mevcut.") 