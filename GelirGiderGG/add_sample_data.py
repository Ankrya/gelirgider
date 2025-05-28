import os
import sys
import random
from datetime import datetime, timedelta
from faker import Faker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import app, db
from src.models.member import Member
from src.models.finance_models import Income, Expense, Bill, Investment, Customer, SalesPackage, Sale

fake = Faker('tr_TR')

with app.app_context():
    member = Member.query.filter_by(username='admin').first()
    if not member:
        print('Admin kullanıcısı bulunamadı!')
        exit(1)
    member_id = member.id

    # Müşteriler
    for _ in range(60):
        c = Customer(
            name=fake.name(),
            email=fake.unique.email(),
            phone=fake.phone_number(),
            address=fake.address(),
            iban=fake.iban(),
            member_id=member_id
        )
        db.session.add(c)
    db.session.commit()
    customers = Customer.query.filter_by(member_id=member_id).all()

    # Satış Paketleri
    for _ in range(60):
        p = SalesPackage(
            name=fake.word().capitalize() + ' Paketi',
            description=fake.sentence(),
            price=round(random.uniform(500, 10000), 2),
            category=fake.word().capitalize(),
            member_id=member_id
        )
        db.session.add(p)
    db.session.commit()
    packages = SalesPackage.query.filter_by(member_id=member_id).all()

    # Gelirler
    for _ in range(60):
        i = Income(
            description=fake.sentence(),
            amount=round(random.uniform(1000, 20000), 2),
            date=fake.date_between(start_date='-1y', end_date='today'),
            category=fake.word().capitalize(),
            member_id=member_id
        )
        db.session.add(i)
    db.session.commit()

    # Giderler
    for _ in range(60):
        e = Expense(
            description=fake.sentence(),
            amount=round(random.uniform(500, 15000), 2),
            date=fake.date_between(start_date='-1y', end_date='today'),
            category=fake.word().capitalize(),
            member_id=member_id
        )
        db.session.add(e)
    db.session.commit()

    # Faturalar
    for _ in range(30):
        b = Bill(
            description=fake.sentence(),
            amount=round(random.uniform(200, 5000), 2),
            due_date=fake.date_between(start_date='-30d', end_date='+30d'),
            status=random.choice(['Unpaid', 'Paid', 'Overdue']),
            member_id=member_id
        )
        db.session.add(b)
    db.session.commit()

    # Satışlar
    for _ in range(30):
        s = Sale(
            customer_id=random.choice(customers).id,
            package_id=random.choice(packages).id,
            sale_date=fake.date_between(start_date='-1y', end_date='today'),
            amount=round(random.uniform(1000, 20000), 2),
            payment_type=random.choice(['Kredi Kartı', 'Nakit', 'Havale/EFT']),
            notes=fake.sentence(),
            member_id=member_id
        )
        db.session.add(s)
    db.session.commit()

    print('300 yeni örnek veri başarıyla eklendi!') 