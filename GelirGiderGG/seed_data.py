import os
import sys
import random
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from src.models.finance_models import db, Income, Expense, Bill, Investment, Customer, SalesPackage, Sale, ImportantFile, BankAccount, BankTransaction
from src.models.user import User
from src.models.member import Member

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:3184156@localhost:3306/mydb"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # Varsayılan bir member ekle (id=1)
    if not Member.query.first():
        member = Member(name="Test Member", email="test@member.com", password="1234")
        db.session.add(member)
        db.session.commit()
    else:
        member = Member.query.first()

    # Customer
    for i in range(50):
        c = Customer(name=f"Müşteri {i}", phone=f"555-000{i:03}", email=f"musteri{i}@mail.com", member_id=member.id)
        db.session.add(c)
    db.session.commit()

    # Income
    for i in range(50):
        inc = Income(description=f"Gelir {i}", amount=random.uniform(100, 1000), date=datetime.now() - timedelta(days=i), member_id=member.id)
        db.session.add(inc)
    db.session.commit()

    # Expense
    for i in range(50):
        exp = Expense(description=f"Gider {i}", amount=random.uniform(50, 500), date=datetime.now() - timedelta(days=i), member_id=member.id)
        db.session.add(exp)
    db.session.commit()

    # Bill
    for i in range(50):
        bill = Bill(description=f"Fatura {i}", amount=random.uniform(20, 200), due_date=datetime.now() + timedelta(days=i), status="Unpaid", member_id=member.id)
        db.session.add(bill)
    db.session.commit()

    # Investment
    for i in range(50):
        inv = Investment(description=f"Yatırım {i}", amount=random.uniform(1000, 10000), date=datetime.now() - timedelta(days=i), member_id=member.id)
        db.session.add(inv)
    db.session.commit()

    # SalesPackage
    for i in range(50):
        sp = SalesPackage(name=f"Paket {i}", price=random.uniform(100, 1000), member_id=member.id)
        db.session.add(sp)
    db.session.commit()

    # Sale
    for i in range(50):
        sale = Sale(description=f"Satış {i}", amount=random.uniform(100, 2000), sale_date=datetime.now() - timedelta(days=i), member_id=member.id)
        db.session.add(sale)
    db.session.commit()

    # ImportantFile
    for i in range(50):
        impf = ImportantFile(filename=f"dosya_{i}.pdf", upload_date=datetime.now() - timedelta(days=i), member_id=member.id)
        db.session.add(impf)
    db.session.commit()

    # BankAccount
    for i in range(5):
        ba = BankAccount(name=f"Banka {i}", iban=f"TR00 0000 0000 0000 0000 000{i:02}", balance=random.uniform(1000, 10000), member_id=member.id)
        db.session.add(ba)
    db.session.commit()

    # BankTransaction
    accounts = BankAccount.query.all()
    for i in range(50):
        acc = random.choice(accounts)
        bt = BankTransaction(account_id=acc.id, amount=random.uniform(-500, 500), date=datetime.now() - timedelta(days=i), description=f"İşlem {i}", member_id=member.id)
        db.session.add(bt)
    db.session.commit()

    print("Her kategori için en az 50 veri başarıyla eklendi!") 