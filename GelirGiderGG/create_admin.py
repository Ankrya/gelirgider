import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app, db
from src.models.member import Member
from werkzeug.security import generate_password_hash

with app.app_context():
    # Admin kullanıcısı var mı kontrol et
    admin = Member.query.filter_by(username='admin').first()
    if not admin:
        # Admin kullanıcısını oluştur
        admin = Member(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('pass')
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin kullanıcısı başarıyla oluşturuldu!")
    else:
        print("Admin kullanıcısı zaten mevcut!") 