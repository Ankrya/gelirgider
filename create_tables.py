import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from src.models.finance_models import db, Income, Expense, Bill, Investment, Customer, SalesPackage, Sale, ImportantFile, BankAccount, BankTransaction
from src.models.user import User
from src.models.member import Member

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:3184156@localhost:3306/mydb"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    print("Tüm tablolar başarıyla oluşturuldu!") 