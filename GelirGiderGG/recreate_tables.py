import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app, db
from src.models.member import Member
from src.models.finance_models import Income, Expense, Bill, Investment, Customer, SalesPackage, Sale, ImportantFile, BankAccount

with app.app_context():
    # Tüm tabloları sil
    db.drop_all()
    print("Tüm tablolar silindi!")
    
    # Tabloları yeniden oluştur
    db.create_all()
    print("Tablolar yeniden oluşturuldu!")
    
    # Admin kullanıcısını oluştur
    from werkzeug.security import generate_password_hash
    admin = Member(
        username='admin',
        email='admin@example.com',
        password_hash=generate_password_hash('pass')
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin kullanıcısı oluşturuldu!") 