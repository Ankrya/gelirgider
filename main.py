import os
import sys
# DON_T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, render_template, request, redirect, url_for, flash, send_file, g, jsonify
from datetime import datetime, timedelta, date
import io
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Import database and models
from src.models.finance_models import db, Income, Expense, Bill, Investment, Customer, SalesPackage, Sale, ImportantFile, BankAccount, BankTransaction
from src.models.user import User
from flask import session
from src.models.member import Member

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'), template_folder='templates')
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://gelirgider:GucluBirSifre123!@localhost/gelirgiderdb"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'odt'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Existing Routes --- 

@app.route('/')
def index():
    today = date.today()
    next_week = today + timedelta(days=7)
    upcoming_bills = Bill.query.filter(
        Bill.due_date.between(today, next_week),
        Bill.status != 'Paid',
        Bill.member_id == session['member_id']
    ).order_by(Bill.due_date).all()
    upcoming_expenses = Expense.query.filter(
        Expense.date.between(today, next_week),
        Expense.member_id == session['member_id']
    ).order_by(Expense.date).all()
    overdue_bills = Bill.query.filter(
        Bill.due_date < today,
        Bill.status != 'Paid',
        Bill.member_id == session['member_id']
    ).order_by(Bill.due_date).all()
    total_upcoming_bills = sum(bill.amount for bill in upcoming_bills)
    total_overdue_bills = sum(bill.amount for bill in overdue_bills)
    total_upcoming_expenses = sum(expense.amount for expense in upcoming_expenses)

    # Dinamik dashboard verileri
    total_customers = Customer.query.filter_by(member_id=session['member_id']).count()
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(Expense.member_id == session['member_id']).scalar() or 0.0
    total_sales = db.session.query(db.func.sum(Sale.amount)).filter(Sale.member_id == session['member_id']).scalar() or 0.0
    total_packages = SalesPackage.query.filter_by(member_id=session['member_id']).count()
    total_investments = Investment.query.filter_by(member_id=session['member_id']).count()
    total_free_users = 0
    total_subscription = 0

    # Gelecek ödemeler: ileri tarihli gelir ve satışlar
    upcoming_sales = Sale.query.filter(
        Sale.sale_date > today,
        Sale.member_id == session['member_id']
    ).order_by(Sale.sale_date).all()

    return render_template('index.html', 
                          upcoming_bills=upcoming_bills,
                          upcoming_expenses=upcoming_expenses,
                          overdue_bills=overdue_bills,
                          total_upcoming_bills=total_upcoming_bills,
                          total_overdue_bills=total_overdue_bills,
                          total_upcoming_expenses=total_upcoming_expenses,
                          today=today,
                          total_customers=total_customers,
                          total_expenses=total_expenses,
                          total_sales=total_sales,
                          total_packages=total_packages,
                          total_investments=total_investments,
                          total_free_users=total_free_users,
                          total_subscription=total_subscription,
                          upcoming_sales=upcoming_sales
    )

@app.route('/delete_bank_account/<int:account_id>', methods=['POST'])
def delete_bank_account(account_id):
    account = BankAccount.query.get_or_404(account_id)
    db.session.delete(account)
    db.session.commit()
    flash('Banka hesabı silindi.', 'success')
    return redirect(url_for('bank_accounts'))

# ... (TÜM ROUTE'LAR VE FONKSİYONLAR BURADA OLACAK) ...

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'templates')):
        os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'))
    app.run(host='0.0.0.0', port=5000, debug=True) 