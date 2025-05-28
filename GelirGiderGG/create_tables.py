import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app, db
from src.models.member import Member
from src.models.finance_models import Income, Expense, Bill, Investment, Customer, SalesPackage, Sale, ImportantFile, BankAccount

with app.app_context():
    db.create_all()
    print("Veritabanı tabloları başarıyla oluşturuldu!") 