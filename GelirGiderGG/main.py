import os
import sys
# DON_T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, render_template, request, redirect, url_for, flash, send_file, g, jsonify, make_response
from datetime import datetime, timedelta, date
import io
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import pdfkit

# Import database and models
from src.models.finance_models import db, Income, Expense, Bill, Investment, Customer, SalesPackage, Sale, ImportantFile, BankAccount, BankTransaction
from src.models.user import User
from flask import session
from src.models.member import Member

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'), template_folder='templates')
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:3184156@localhost:3306/mydb"
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
    range = request.args.get('range', 'all')
    today = date.today()
    if range == 'today':
        start_date = today
    elif range == 'week':
        start_date = today - timedelta(days=6)
    elif range == 'month':
        start_date = today.replace(day=1)
    else:
        start_date = None

    member_id = session['member_id']
    # Fatura ve giderler için filtre
    bill_filters = [Bill.member_id == member_id]
    expense_filters = [Expense.member_id == member_id]
    sale_filters = [Sale.member_id == member_id]
    if start_date:
        bill_filters.append(Bill.due_date >= start_date)
        expense_filters.append(Expense.date >= start_date)
        sale_filters.append(Sale.sale_date >= start_date)

    next_week = today + timedelta(days=7)
    upcoming_bills = Bill.query.filter(*bill_filters, Bill.due_date.between(today, next_week), Bill.status != 'Paid').order_by(Bill.due_date).all()
    upcoming_expenses = Expense.query.filter(*expense_filters, Expense.date.between(today, next_week)).order_by(Expense.date).all()
    overdue_bills = Bill.query.filter(*bill_filters, Bill.due_date < today, Bill.status != 'Paid').order_by(Bill.due_date).all()
    total_upcoming_bills = sum(bill.amount for bill in upcoming_bills)
    total_overdue_bills = sum(bill.amount for bill in overdue_bills)
    total_upcoming_expenses = sum(expense.amount for expense in upcoming_expenses)

    # Dinamik dashboard verileri
    total_customers = Customer.query.filter_by(member_id=member_id).count()
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(*expense_filters).scalar() or 0.0
    total_sales = db.session.query(db.func.sum(Sale.amount)).filter(*sale_filters).scalar() or 0.0
    total_packages = SalesPackage.query.filter_by(member_id=member_id).count()
    total_investments = Investment.query.filter_by(member_id=member_id).count()
    total_free_users = 0
    total_subscription = 0

    # Gelecek ödemeler: ileri tarihli gelir ve satışlar
    upcoming_sales = Sale.query.filter(*sale_filters, Sale.sale_date > today).order_by(Sale.sale_date).all()

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
                          upcoming_sales=upcoming_sales,
                          range=range
    )

@app.route('/income', methods=['GET', 'POST'])
def income():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        date_str = request.form['date']
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        category = request.form.get('category')
        new_income = Income(description=description, amount=amount, date=date_obj, category=category, member_id=session['member_id'])
        db.session.add(new_income)
        db.session.commit()
        flash('Gelir başarıyla eklendi!', 'success')
        return redirect(url_for('income'))
    incomes = Income.query.filter_by(member_id=session['member_id']).all()
    return render_template('income.html', incomes=incomes)

@app.route('/delete_income/<int:income_id>', methods=['POST'])
def delete_income(income_id):
    income_to_delete = Income.query.filter_by(id=income_id, member_id=session['member_id']).first_or_404()
    db.session.delete(income_to_delete)
    db.session.commit()
    flash('Gelir başarıyla silindi!', 'success')
    return redirect(url_for('income'))

@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        date_str = request.form['date']
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        category = request.form.get('category')
        customer_id = request.form.get('customer_id')
        if customer_id and customer_id != '':
            new_expense = Expense(description=description, amount=amount, date=date_obj, category=category, member_id=session['member_id'], customer_id=int(customer_id))
        else:
            new_expense = Expense(description=description, amount=amount, date=date_obj, category=category, member_id=session['member_id'])
        db.session.add(new_expense)
        db.session.commit()
        flash('Gider başarıyla eklendi!', 'success')
        return redirect(url_for('expenses'))
    # Sıralama parametreleri
    sort = request.args.get('sort', 'date')
    order = request.args.get('order', 'desc')
    valid_sorts = {
        'date': Expense.date,
        'description': Expense.description,
        'amount': Expense.amount,
        'category': Expense.category
    }
    sort_col = valid_sorts.get(sort, Expense.date)
    if order == 'asc':
        expenses = Expense.query.filter_by(member_id=session['member_id']).order_by(sort_col.asc()).all()
    else:
        expenses = Expense.query.filter_by(member_id=session['member_id']).order_by(sort_col.desc()).all()
    customers = Customer.query.filter_by(member_id=session['member_id']).order_by(Customer.name.asc()).all()
    return render_template('expenses.html', expenses=expenses, sort=sort, order=order, customers=customers)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense_to_delete = Expense.query.filter_by(id=expense_id, member_id=session['member_id']).first_or_404()
    db.session.delete(expense_to_delete)
    db.session.commit()
    flash('Gider başarıyla silindi!', 'success')
    return redirect(url_for('expenses'))

@app.route('/bills', methods=['GET', 'POST'])
def bills():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        due_date_str = request.form['due_date']
        due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        status = request.form.get('status', 'Unpaid')
        new_bill = Bill(description=description, amount=amount, due_date=due_date_obj, status=status, member_id=session['member_id'])
        db.session.add(new_bill)
        # Fatura ile birlikte gider de ekle
        new_expense = Expense(description=description, amount=amount, date=due_date_obj, category='Fatura', member_id=session['member_id'])
        db.session.add(new_expense)
        db.session.commit()
        flash('Fatura ve ilgili gider başarıyla eklendi!', 'success')
        return redirect(url_for('bills'))
    # Sıralama parametreleri
    sort = request.args.get('sort', 'due_date')
    order = request.args.get('order', 'desc')
    valid_sorts = {
        'due_date': Bill.due_date,
        'description': Bill.description,
        'amount': Bill.amount,
        'status': Bill.status
    }
    sort_col = valid_sorts.get(sort, Bill.due_date)
    if order == 'asc':
        bills = Bill.query.filter_by(member_id=session['member_id']).order_by(sort_col.asc()).all()
    else:
        bills = Bill.query.filter_by(member_id=session['member_id']).order_by(sort_col.desc()).all()
    return render_template('bills.html', bills=bills, sort=sort, order=order)

@app.route('/delete_bill/<int:bill_id>', methods=['POST'])
def delete_bill(bill_id):
    bill_to_delete = Bill.query.filter_by(id=bill_id, member_id=session['member_id']).first_or_404()
    db.session.delete(bill_to_delete)
    db.session.commit()
    flash('Fatura başarıyla silindi!', 'success')
    return redirect(url_for('bills'))

@app.route('/update_bill_status/<int:bill_id>', methods=['POST'])
def update_bill_status(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    new_status = request.form.get('status')
    if new_status in ['Paid', 'Unpaid', 'Overdue']:
        bill.status = new_status
        db.session.commit()
        flash(f'Fatura durumu "{new_status}" olarak güncellendi!', 'success')
    else:
        flash('Geçersiz durum değeri!', 'error')
    
    # Redirect back to the referring page (either bills page or homepage)
    referrer = request.referrer
    if referrer and 'bills' in referrer:
        return redirect(url_for('bills'))
    return redirect(url_for('index'))

@app.route('/investments', methods=['GET', 'POST'])
def investments():
    if request.method == 'POST':
        name = request.form['name']
        inv_type = request.form.get('type')
        amount_invested = float(request.form['amount_invested'])
        purchase_date_str = request.form['purchase_date']
        purchase_date_obj = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        current_value = request.form.get('current_value')
        current_value = float(current_value) if current_value else None
        new_investment = Investment(name=name, type=inv_type, amount_invested=amount_invested, purchase_date=purchase_date_obj, current_value=current_value, member_id=session['member_id'])
        db.session.add(new_investment)
        db.session.commit()
        flash('Yatırım başarıyla eklendi!', 'success')
        return redirect(url_for('investments'))
    sort = request.args.get('sort', 'purchase_date')
    order = request.args.get('order', 'desc')
    valid_sorts = {
        'name': Investment.name,
        'type': Investment.type,
        'amount_invested': Investment.amount_invested,
        'purchase_date': Investment.purchase_date,
        'current_value': Investment.current_value
    }
    sort_col = valid_sorts.get(sort, Investment.purchase_date)
    if order == 'asc':
        investments = Investment.query.filter_by(member_id=session['member_id']).order_by(sort_col.asc()).all()
    else:
        investments = Investment.query.filter_by(member_id=session['member_id']).order_by(sort_col.desc()).all()
    return render_template('investments.html', investments=investments, sort=sort, order=order)

@app.route('/delete_investment/<int:investment_id>', methods=['POST'])
def delete_investment(investment_id):
    investment_to_delete = Investment.query.filter_by(id=investment_id, member_id=session['member_id']).first_or_404()
    db.session.delete(investment_to_delete)
    db.session.commit()
    flash('Yatırım başarıyla silindi!', 'success')
    return redirect(url_for('investments'))

@app.route('/reports')
def reports():
    member_id = session['member_id']
    # Filtreler
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    tx_type = request.args.get('type', 'all')
    category = request.args.get('category', 'all')

    # Kategoriler
    all_categories = sorted(set([e.category for e in Expense.query.filter_by(member_id=member_id) if e.category] + [i.category for i in Income.query.filter_by(member_id=member_id) if i.category]))

    # Filtreli işlemler
    income_query = Income.query.filter_by(member_id=member_id)
    expense_query = Expense.query.filter_by(member_id=member_id)
    if start_date:
        income_query = income_query.filter(Income.date >= start_date)
        expense_query = expense_query.filter(Expense.date >= start_date)
    if end_date:
        income_query = income_query.filter(Income.date <= end_date)
        expense_query = expense_query.filter(Expense.date <= end_date)
    if category != 'all':
        income_query = income_query.filter(Income.category == category)
        expense_query = expense_query.filter(Expense.category == category)
    if tx_type == 'income':
        expense_query = expense_query.filter(Expense.id == -1)  # Boş
    elif tx_type == 'expense':
        income_query = income_query.filter(Income.id == -1)  # Boş
    incomes = income_query.all() or []
    expenses = expense_query.all() or []

    # Özetler
    total_income = sum(i.amount for i in incomes) if incomes else 0.0
    total_expenses = sum(e.amount for e in expenses) if expenses else 0.0
    net_savings = total_income - total_expenses

    # Kategori bazlı özet
    category_summary = []
    all_items = []
    for i in incomes:
        all_items.append({'category': i.category or 'Diğer', 'type': 'income', 'amount': i.amount})
    for e in expenses:
        all_items.append({'category': e.category or 'Diğer', 'type': 'expense', 'amount': e.amount})
    from collections import defaultdict
    cat_groups = {}
    for item in all_items:
        key = (item['category'], item['type'])
        if key not in cat_groups:
            cat_groups[key] = {'category': item['category'], 'type': item['type'], 'count': 0, 'total': 0.0}
        cat_groups[key]['count'] += 1
        cat_groups[key]['total'] += item['amount']
    total_all = sum(x['total'] for x in cat_groups.values()) or 1
    for v in cat_groups.values():
        v['percent'] = 100 * v['total'] / total_all
        category_summary.append(v)
    category_summary = sorted(category_summary, key=lambda x: -x['total'])

    # Grafik: Aylık trend
    import calendar
    trend = defaultdict(lambda: {'income': 0, 'expense': 0})
    for i in incomes:
        key = i.date.strftime('%b %Y')
        trend[key]['income'] += i.amount
    for e in expenses:
        key = e.date.strftime('%b %Y')
        trend[key]['expense'] += e.amount
    trend_labels = list(sorted(trend.keys(), key=lambda x: (int(x.split()[1]), list(calendar.month_abbr).index(x.split()[0])))) if trend else []
    trend_income = [trend[k]['income'] for k in trend_labels] if trend_labels else []
    trend_expense = [trend[k]['expense'] for k in trend_labels] if trend_labels else []

    # Grafik: Kategori dağılımı
    cat_totals = defaultdict(float)
    for i in incomes:
        cat_totals[i.category or 'Diğer'] += i.amount
    for e in expenses:
        cat_totals[e.category or 'Diğer'] += e.amount
    category_labels = list(cat_totals.keys()) if cat_totals else []
    category_data = [cat_totals[k] for k in category_labels] if category_labels else []

    return render_template('reports.html',
        total_income=total_income,
        total_expenses=total_expenses,
        net_savings=net_savings,
        categories=all_categories or [],
        category_summary=category_summary or [],
        trend_labels=trend_labels or [],
        trend_income=trend_income or [],
        trend_expense=trend_expense or [],
        category_labels=category_labels or [],
        category_data=category_data or []
    )

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        iban = request.form.get('iban')
        new_customer = Customer(
            name=name,
            email=email,
            phone=phone,
            address=address,
            iban=iban,
            member_id=session['member_id']
        )
        db.session.add(new_customer)
        db.session.commit()
        flash('Müşteri başarıyla eklendi!', 'success')
        return redirect(url_for('customers'))

    query = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')
    valid_sorts = {
        'name': Customer.name,
        'email': Customer.email,
        'phone': Customer.phone,
        'address': Customer.address,
        'iban': Customer.iban
    }
    sort_col = valid_sorts.get(sort, Customer.name)
    base_query = Customer.query.filter_by(member_id=session['member_id'])
    if query:
        customers = base_query.filter(Customer.name.ilike(f'%{query}%'))
    else:
        customers = base_query
    if order == 'desc':
        customers = customers.order_by(sort_col.desc())
    else:
        customers = customers.order_by(sort_col.asc())
    customers = customers.all()
    return render_template('customers.html', customers=customers, query=query, sort=sort, order=order)

@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    customer_to_delete = Customer.query.filter_by(id=customer_id, member_id=session['member_id']).first_or_404()
    db.session.delete(customer_to_delete)
    db.session.commit()
    flash('Müşteri başarıyla silindi!', 'success')
    return redirect(url_for('customers'))

@app.route('/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    customer = Customer.query.filter_by(id=customer_id, member_id=session['member_id']).first_or_404()
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.address = request.form.get('address')
        customer.iban = request.form.get('iban')
        db.session.commit()
        flash('Müşteri başarıyla güncellendi!', 'success')
        return redirect(url_for('customers'))
    return render_template('edit_customer.html', customer=customer)

@app.route('/sales_packages', methods=['GET', 'POST'])
def sales_packages():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form.get('category')
        package = SalesPackage(name=name, description=description, price=price, category=category, member_id=session['member_id'])
        db.session.add(package)
        db.session.commit()
        flash('Satış paketi başarıyla eklendi.', 'success')
        return redirect(url_for('sales_packages'))
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')
    valid_sorts = {
        'name': SalesPackage.name,
        'price': SalesPackage.price,
        'category': SalesPackage.category
    }
    sort_col = valid_sorts.get(sort, SalesPackage.name)
    packages = SalesPackage.query.filter_by(member_id=session['member_id'])
    if order == 'desc':
        packages = packages.order_by(sort_col.desc())
    else:
        packages = packages.order_by(sort_col.asc())
    packages = packages.all()
    return render_template('sales_packages.html', packages=packages, sort=sort, order=order)

@app.route('/edit_sales_package/<int:package_id>', methods=['GET', 'POST'])
def edit_sales_package(package_id):
    package = SalesPackage.query.get_or_404(package_id)
    if package.member_id != session['member_id']:
        flash('Bu işlem için yetkiniz yok.', 'danger')
        return redirect(url_for('sales_packages'))
    if request.method == 'POST':
        package.name = request.form['name']
        package.description = request.form['description']
        package.price = float(request.form['price'])
        package.category = request.form.get('category')
        db.session.commit()
        flash('Satış paketi başarıyla güncellendi.', 'success')
        return redirect(url_for('sales_packages'))
    return render_template('edit_sales_package.html', package=package)

@app.route('/delete_sales_package/<int:package_id>', methods=['POST'])
def delete_sales_package(package_id):
    package = SalesPackage.query.get_or_404(package_id)
    if package.member_id != session['member_id']:
        flash('Bu işlem için yetkiniz yok.', 'danger')
        return redirect(url_for('sales_packages'))
    db.session.delete(package)
    db.session.commit()
    flash('Satış paketi başarıyla silindi.', 'success')
    return redirect(url_for('sales_packages'))

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if request.method == 'POST':
        customer_id = int(request.form['customer_id'])
        package_id = int(request.form['package_id'])
        sale_date_str = request.form['sale_date']
        sale_date_obj = datetime.strptime(sale_date_str, '%Y-%m-%d').date()
        amount_str = request.form['amount']
        if amount_str.strip() == '':
            # Paket fiyatını kullan
            package = SalesPackage.query.get(package_id)
            amount = package.price if package else 0.0
        else:
            amount = float(amount_str)
        payment_type = request.form['payment_type']
        notes = request.form.get('notes')
        new_sale = Sale(customer_id=customer_id, package_id=package_id, sale_date=sale_date_obj, amount=amount, payment_type=payment_type, notes=notes, member_id=session['member_id'])
        db.session.add(new_sale)
        db.session.commit()
        flash('Satış başarıyla kaydedildi!', 'success')
        return redirect(url_for('sales'))
    sort = request.args.get('sort', 'sale_date')
    order = request.args.get('order', 'desc')
    valid_sorts = {
        'sale_date': Sale.sale_date,
        'amount': Sale.amount,
        'payment_type': Sale.payment_type
    }
    sort_col = valid_sorts.get(sort, Sale.sale_date)
    all_sales = Sale.query.filter_by(member_id=session['member_id']).join(Customer).join(SalesPackage)
    if sort == 'customer':
        if order == 'asc':
            all_sales = all_sales.order_by(Customer.name.asc())
        else:
            all_sales = all_sales.order_by(Customer.name.desc())
    elif sort == 'package':
        if order == 'asc':
            all_sales = all_sales.order_by(SalesPackage.name.asc())
        else:
            all_sales = all_sales.order_by(SalesPackage.name.desc())
    else:
        if order == 'asc':
            all_sales = all_sales.order_by(sort_col.asc())
        else:
            all_sales = all_sales.order_by(sort_col.desc())
    all_sales = all_sales.all()
    all_customers = Customer.query.filter_by(member_id=session['member_id']).all()
    all_packages = SalesPackage.query.filter_by(member_id=session['member_id']).all()
    payment_types = ['Kredi Kartı', 'Nakit', 'Havale/EFT', 'Çek', 'Senet', 'Vadeli Ödeme']
    return render_template('sales.html', sales=all_sales, customers=all_customers, packages=all_packages, payment_types=payment_types, sort=sort, order=order)

@app.route('/delete_sale/<int:sale_id>', methods=['POST'])
def delete_sale(sale_id):
    sale_to_delete = Sale.query.filter_by(id=sale_id, member_id=session['member_id']).first_or_404()
    db.session.delete(sale_to_delete)
    db.session.commit()
    flash('Satış başarıyla silindi!', 'success')
    return redirect(url_for('sales'))

@app.route('/export_excel')
def export_excel():
    range_type = request.args.get('range_type', 'daily')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filters = [Income.member_id == session['member_id']]
    if start_date and end_date:
        filters.append(Income.date.between(start_date, end_date))
        filters_exp = [Expense.member_id == session['member_id'], Expense.date.between(start_date, end_date)]
        filters_bill = [Bill.member_id == session['member_id'], Bill.due_date.between(start_date, end_date)]
        filters_sale = [Sale.member_id == session['member_id'], Sale.sale_date.between(start_date, end_date)]
    else:
        filters_exp = [Expense.member_id == session['member_id']]
        filters_bill = [Bill.member_id == session['member_id']]
        filters_sale = [Sale.member_id == session['member_id']]
    incomes = Income.query.filter(*filters).all()
    df_incomes = pd.DataFrame([{
        'Açıklama': i.description,
        'Miktar': i.amount,
        'Tarih': i.date,
        'Kategori': i.category
    } for i in incomes])
    expenses = Expense.query.filter(*filters_exp).all()
    df_expenses = pd.DataFrame([{
        'Açıklama': e.description,
        'Miktar': e.amount,
        'Tarih': e.date,
        'Kategori': e.category
    } for e in expenses])
    bills = Bill.query.filter(*filters_bill).all()
    df_bills = pd.DataFrame([{
        'Açıklama': b.description,
        'Miktar': b.amount,
        'Son Ödeme Tarihi': b.due_date,
        'Durum': b.status
    } for b in bills])
    sales = Sale.query.filter(*filters_sale).all()
    df_sales = pd.DataFrame([{
        'Müşteri': s.customer.name if s.customer else '-',
        'Paket': s.package.name if s.package else '-',
        'Satış Tarihi': s.sale_date,
        'Tutar': s.amount,
        'Ödeme Türü': s.payment_type,
        'Notlar': s.notes
    } for s in sales])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_incomes.to_excel(writer, index=False, sheet_name='Gelirler')
        df_expenses.to_excel(writer, index=False, sheet_name='Giderler')
        df_bills.to_excel(writer, index=False, sheet_name='Faturalar')
        df_sales.to_excel(writer, index=False, sheet_name='Satışlar')
    output.seek(0)
    return send_file(output, download_name='rapor.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/export_csv')
def export_csv():
    range_type = request.args.get('range_type', 'daily')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    filters = [Income.member_id == session['member_id']]
    if start_date and end_date:
        filters.append(Income.date.between(start_date, end_date))
        filters_exp = [Expense.member_id == session['member_id'], Expense.date.between(start_date, end_date)]
        filters_bill = [Bill.member_id == session['member_id'], Bill.due_date.between(start_date, end_date)]
        filters_sale = [Sale.member_id == session['member_id'], Sale.sale_date.between(start_date, end_date)]
    else:
        filters_exp = [Expense.member_id == session['member_id']]
        filters_bill = [Bill.member_id == session['member_id']]
        filters_sale = [Sale.member_id == session['member_id']]
    incomes = Income.query.filter(*filters).all()
    df_incomes = pd.DataFrame([{
        'Açıklama': i.description,
        'Miktar': i.amount,
        'Tarih': i.date,
        'Kategori': i.category
    } for i in incomes])
    expenses = Expense.query.filter(*filters_exp).all()
    df_expenses = pd.DataFrame([{
        'Açıklama': e.description,
        'Miktar': e.amount,
        'Tarih': e.date,
        'Kategori': e.category
    } for e in expenses])
    bills = Bill.query.filter(*filters_bill).all()
    df_bills = pd.DataFrame([{
        'Açıklama': b.description,
        'Miktar': b.amount,
        'Son Ödeme Tarihi': b.due_date,
        'Durum': b.status
    } for b in bills])
    sales = Sale.query.filter(*filters_sale).all()
    df_sales = pd.DataFrame([{
        'Müşteri': s.customer.name if s.customer else '-',
        'Paket': s.package.name if s.package else '-',
        'Satış Tarihi': s.sale_date,
        'Tutar': s.amount,
        'Ödeme Türü': s.payment_type,
        'Notlar': s.notes
    } for s in sales])
    output = io.StringIO()
    df_incomes.to_csv(output, index=False, encoding='utf-8-sig')
    df_expenses.to_csv(output, index=False, encoding='utf-8-sig')
    df_bills.to_csv(output, index=False, encoding='utf-8-sig')
    df_sales.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), download_name='rapor.csv', as_attachment=True, mimetype='text/csv')

@app.route('/<path:path>')
def serve_static_path(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "File not found", 404

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if Member.query.filter((Member.username == username) | (Member.email == email)).first():
            flash('Bu kullanıcı adı veya e-posta zaten kayıtlı!', 'danger')
            return render_template('register.html')
        password_hash = generate_password_hash(password)
        new_member = Member(username=username, email=email, password_hash=password_hash)
        db.session.add(new_member)
        db.session.commit()
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('member_id'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        member = Member.query.filter_by(username=username).first()
        if member and check_password_hash(member.password_hash, password):
            session['member_id'] = member.id
            session['member_username'] = member.username
            flash('Giriş başarılı!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Kullanıcı adı veya şifre hatalı!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Çıkış yapıldı.', 'success')
    return redirect(url_for('login'))

@app.before_request
def require_login():
    open_routes = ['login', 'register', 'static']
    if request.endpoint not in open_routes and not session.get('member_id'):
        return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
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

@app.route('/add_example_packages')
def add_example_packages():
    example_packages = [
        ("Web ve Dijital Altyapı Hizmetleri", "Web Site", "Kurumsal kimliğinizi yansıtan, mobil uyumlu, SEO altyapısına sahip modern web siteleri tasarımı."),
        ("Web ve Dijital Altyapı Hizmetleri", "E-Ticaret Paketleri", "Yeni başlayan işletmeler için altyapıdan tasarıma kadar her şeyi içeren e-ticaret çözümleri."),
        ("Web ve Dijital Altyapı Hizmetleri", "Restoran QR Menü", "QR kodla erişilen dijital menülerle restoran deneyimini temassız, şık ve modern hale getirme."),
        ("SEO ve Görünürlük Artırma", "SEO Hizmetleri", "Teknik analiz, anahtar kelime optimizasyonu ve backlink stratejileriyle web sitenizi üst sıralara taşıma."),
        ("SEO ve Görünürlük Artırma", "Haritalar Sıra Yükseltme", "Google Haritalar'da işletmenizi öne çıkararak daha fazla yerel müşteriye ulaşmanızı sağlama."),
        ("SEO ve Görünürlük Artırma", "İçerik Yazarlığı (Blog + SEO)", "SEO uyumlu, etkileyici içeriklerle web sitenizin organik görünürlüğünü artırma."),
        ("Dijital Pazarlama ve Reklam", "Reklam Yönetimi", "Google, Meta ve diğer dijital platformlarda reklamlarınızı hedef kitlenize ulaşacak şekilde optimize etme."),
        ("Dijital Pazarlama ve Reklam", "Sosyal Medya Post Tasarımı", "Marka kimliğinize uygun özgün post tasarımlarıyla sosyal medya görünümünüzü güçlendirme."),
        ("Dijital Pazarlama ve Reklam", "Sosyal Medya Yönetimi", "Tüm sosyal medya hesaplarınızı profesyonel şekilde yönetme, içerik üretimi ve etkileşim stratejileri geliştirme."),
        ("Görsel İçerik Üretimi", "Drone Çekim", "Yüksek çözünürlüklü hava çekimleriyle tanıtım videolarınıza sinematik bir dokunuş katma."),
        ("Görsel İçerik Üretimi", "Sanal Drone Çekimi", "Gerçek çekim olmadan dijital olarak hazırlanan sanal uçuş videolarıyla projelerinizi etkileyici biçimde sergileme."),
        ("Görsel İçerik Üretimi", "Video Prodüksiyon", "Senaryodan kurguya kadar her aşamada profesyonel video içerikler üretme."),
        ("Görsel İçerik Üretimi", "Ürün Fotoğrafçılığı", "E-ticaret ve sosyal medya için profesyonel stüdyo ortamında yüksek kaliteli ürün çekimleri yapma."),
        ("Görsel İçerik Üretimi", "Stüdyo Araç Çekimi", "Araçlarınız için özel olarak kurgulanmış stüdyo ortamında yüksek kaliteli ve estetik çekimler yapma."),
        ("Marka ve Strateji Geliştirme", "Marka Danışmanlığı", "Markanızın kimliğini oluşturmak, konumlandırmak ve etkili şekilde sunmak için stratejik destek sağlama."),
        ("Marka ve Strateji Geliştirme", "Kurumsal Kimlik Tasarımı", "Logo, kartvizit, sunum şablonu gibi tüm görsel materyallerle kurumsal kimliğinizi bir bütün haline getirme."),
        ("Marka ve Strateji Geliştirme", "Eğitim ve Danışmanlık", "İşletmelere ve bireylere dijital pazarlama, sosyal medya ve içerik üretimi konularında özel eğitimler verme."),
        ("Basılı ve Dijital Ürünler", "Baskı Hizmetleri", "Kartvizit, broşür, menü gibi tüm basılı materyallerde kaliteli ve hızlı baskı çözümleri sağlama."),
        ("Basılı ve Dijital Ürünler", "Reklam Afişi", "Etkileyici tasarımlar ve dikkat çekici mesajlarla hazırlanan reklam afişleriyle markanızı güçlü şekilde temsil etme."),
        ("Basılı ve Dijital Ürünler", "Neon Tabela", "Özel tasarım ve kaliteli malzemelerle uzun ömürlü neon tabelalarla mekanınıza karakter katma."),
        ("Dijital Kod Satışı", "Oyun Kodları Satışı", "Steam, Xbox, PlayStation, Epic Games gibi platformlara ait dijital oyun kodlarını müşterilerinize sunma."),
        ("Dijital Kod Satışı", "Yazılım Lisansları", "Windows, Office, antivirüs ve profesyonel yazılım lisanslarını güvenilir kaynaklardan temin etme."),
        ("Dijital Kod Satışı", "Ön Ödemeli Kart & Hediye Kodları", "Netflix, Spotify, Google Play, App Store gibi platformlara ait ön ödemeli kart ve hediye kodlarının satışını sağlama."),
        ("Çekim ve Görsel İçerik Üretimi", "Etkinlik Çekimi", "Konser, düğün, kurumsal lansman gibi etkinliklerin profesyonel video ve fotoğraf çekimi."),
        ("Çekim ve Görsel İçerik Üretimi", "Reklam Filmi Çekimi", "Dijital ve TV platformları için kreatif ve sinematik kısa reklam filmleri."),
        ("Çekim ve Görsel İçerik Üretimi", "Kurumsal Tanıtım Filmi", "Kurumların faaliyetlerini ve değerlerini anlatan profesyonel tanıtım videoları."),
        ("Çekim ve Görsel İçerik Üretimi", "Moda / Katalog Çekimi", "Tekstil ve moda ürünleri için mankenli veya still-life katalog çekimleri."),
        ("Çekim ve Görsel İçerik Üretimi", "360° Fotoğraf ve Video Çekimi", "VR uyumlu panoramik çekimlerle mekan ve ürün tanıtımı."),
        ("Çekim ve Görsel İçerik Üretimi", "Time-Lapse Çekim", "İnşaat veya etkinlik kurulumlarının hızlandırılmış görsel anlatımı."),
        ("Çekim ve Görsel İçerik Üretimi", "Green Screen Çekimi", "Arka plan değişikliğine uygun yeşil perde ile çekim hizmeti."),
        ("Çekim ve Görsel İçerik Üretimi", "Sosyal Medya Video Paketi", "Reels, TikTok ve Shorts için kısa, hızlı kurgulanmış videolar."),
        ("Çekim ve Görsel İçerik Üretimi", "Gece Drone Çekimi", "Mekanların gece estetiğini yansıtan düşük ışıkta hava çekimi."),
        ("Çekim ve Görsel İçerik Üretimi", "Canlı Yayın Hizmeti", "Etkinliklerin sosyal medya platformlarında canlı yayınlanması."),
        ("Çekim ve Görsel İçerik Üretimi", "Bebek Fotoğraf / Video Çekimi", "Yeni doğan ve çocuklar için özel fotoğraf ve video prodüksiyonu.")
    ]
    member_id = session.get('member_id')
    if not member_id:
        return "Giriş yapmalısınız!", 403
    for kategori, hizmet_adi, aciklama in example_packages:
        # Aynı isimde paket varsa ekleme
        if not SalesPackage.query.filter_by(name=hizmet_adi, member_id=member_id).first():
            new_package = SalesPackage(name=hizmet_adi, description=f"{kategori}: {aciklama}", price=1000, category=kategori, member_id=member_id)
            db.session.add(new_package)
    db.session.commit()
    return "Örnek paketler başarıyla eklendi!"

@app.route('/add_example_data')
def add_example_data():
    member_id = session.get('member_id')
    if not member_id:
        return "Giriş yapmalısınız!", 403

    # Müşteriler
    example_customers = [
        ("Ahmet Yılmaz", "ahmet@example.com", "5551112233", "İstanbul"),
        ("Ayşe Demir", "ayse@example.com", "5552223344", "Ankara"),
        ("Mehmet Kaya", "mehmet@example.com", "5553334455", "İzmir"),
        ("Zeynep Çelik", "zeynep@example.com", "5554445566", "Bursa"),
        ("Ali Vural", "ali@example.com", "5555556677", "Antalya")
    ]
    for name, email, phone, address in example_customers:
        if not Customer.query.filter_by(name=name, member_id=member_id).first():
            db.session.add(Customer(name=name, email=email, phone=phone, address=address, member_id=member_id))

    # Gelirler
    from datetime import timedelta
    today = date.today()
    example_incomes = [
        ("Web Site Satışı", 5000, today - timedelta(days=10), "Web"),
        ("SEO Hizmeti", 2000, today - timedelta(days=5), "SEO"),
        ("E-Ticaret Paketi", 8000, today + timedelta(days=3), "E-Ticaret"), # ileri tarihli
        ("Danışmanlık", 1500, today, "Danışmanlık")
    ]
    for desc, amount, dt, cat in example_incomes:
        if not Income.query.filter_by(description=desc, member_id=member_id).first():
            db.session.add(Income(description=desc, amount=amount, date=dt, category=cat, member_id=member_id))

    # Giderler
    example_expenses = [
        ("Ofis Kirası", 2500, today - timedelta(days=2), "Kira"),
        ("Domain Yenileme", 200, today + timedelta(days=4), "Web"), # ileri tarihli
        ("Elektrik Faturası", 350, today, "Fatura"),
        ("Yazılım Lisansı", 1200, today - timedelta(days=7), "Lisans")
    ]
    for desc, amount, dt, cat in example_expenses:
        if not Expense.query.filter_by(description=desc, member_id=member_id).first():
            db.session.add(Expense(description=desc, amount=amount, date=dt, category=cat, member_id=member_id))

    # Faturalar
    example_bills = [
        ("Hosting", 400, today + timedelta(days=2), "Unpaid"), # yaklaşan
        ("Sunucu", 900, today - timedelta(days=1), "Unpaid"), # gecikmiş
        ("Ofis Temizlik", 300, today + timedelta(days=8), "Unpaid"), # ileri tarihli
        ("Telefon", 150, today, "Paid")
    ]
    for desc, amount, due, status in example_bills:
        if not Bill.query.filter_by(description=desc, member_id=member_id).first():
            db.session.add(Bill(description=desc, amount=amount, due_date=due, status=status, member_id=member_id))

    # Yatırımlar
    example_investments = [
        ("Borsa Hissesi", "Hisse", 10000, today - timedelta(days=30), 12000),
        ("Altın", "Emtia", 5000, today - timedelta(days=60), 5500)
    ]
    for name, typ, invested, purchase, current in example_investments:
        if not Investment.query.filter_by(name=name, member_id=member_id).first():
            db.session.add(Investment(name=name, type=typ, amount_invested=invested, purchase_date=purchase, current_value=current, member_id=member_id))

    # Satışlar (biri ileri tarihli)
    customers = Customer.query.filter_by(member_id=member_id).all()
    packages = SalesPackage.query.filter_by(member_id=member_id).all()
    if customers and packages:
        from random import choice
        example_sales = [
            (customers[0].id, packages[0].id, today - timedelta(days=1), 5000, "Kredi Kartı", ""),
            (customers[1].id, packages[1].id, today + timedelta(days=5), 8000, "Nakit", "İleri tarihli satış"), # ileri tarihli
            (customers[2].id, packages[2].id, today, 2000, "Havale/EFT", "")
        ]
        for cust_id, pack_id, sale_date, amount, pay_type, notes in example_sales:
            if not Sale.query.filter_by(customer_id=cust_id, package_id=pack_id, sale_date=sale_date, member_id=member_id).first():
                db.session.add(Sale(customer_id=cust_id, package_id=pack_id, sale_date=sale_date, amount=amount, payment_type=pay_type, notes=notes, member_id=member_id))

    db.session.commit()
    return "Tüm örnek veriler başarıyla eklendi!"

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    member_id = session.get('member_id')
    if not member_id:
        return redirect(url_for('login'))
    member = Member.query.get(member_id)
    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        if email:
            member.email = email
        if phone is not None:
            member.phone = phone
        if password:
            member.password_hash = generate_password_hash(password)
        db.session.commit()
        flash('Profiliniz güncellendi.', 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', member=member)

@app.route('/important_files', methods=['GET', 'POST'])
def important_files():
    member_id = session.get('member_id')
    if not member_id:
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('Dosya seçilmedi.', 'danger')
        elif not allowed_file(file.filename):
            flash('Sadece doküman dosyaları yükleyebilirsiniz.', 'danger')
        else:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            db.session.add(ImportantFile(filename=filename, filepath=save_path, member_id=member_id))
            db.session.commit()
            flash('Dosya başarıyla yüklendi.', 'success')
        return redirect(url_for('important_files'))
    files = ImportantFile.query.filter_by(member_id=member_id).order_by(ImportantFile.upload_date.desc()).all()
    return render_template('important_files.html', files=files)

@app.route('/download_file/<int:file_id>')
def download_file(file_id):
    member_id = session.get('member_id')
    file = ImportantFile.query.filter_by(id=file_id, member_id=member_id).first_or_404()
    return send_file(file.filepath, as_attachment=True, download_name=file.filename)

@app.route('/delete_file/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    member_id = session.get('member_id')
    file = ImportantFile.query.filter_by(id=file_id, member_id=member_id).first_or_404()
    try:
        if os.path.exists(file.filepath):
            os.remove(file.filepath)
    except Exception:
        pass
    db.session.delete(file)
    db.session.commit()
    flash('Dosya silindi.', 'success')
    return redirect(url_for('important_files'))

def get_notifications():
    notifications = []
    member_id = session.get('member_id')
    if not member_id:
        return notifications
    # Yaklaşan faturalar
    from datetime import date, timedelta
    today = date.today()
    next_week = today + timedelta(days=7)
    upcoming_bills = Bill.query.filter(
        Bill.due_date.between(today, next_week),
        Bill.status != 'Paid',
        Bill.member_id == member_id
    ).all()
    for bill in upcoming_bills:
        notifications.append(f"Yaklaşan fatura: {bill.description} - {bill.due_date.strftime('%d.%m.%Y')}")
    # Geciken faturalar
    overdue_bills = Bill.query.filter(
        Bill.due_date < today,
        Bill.status != 'Paid',
        Bill.member_id == member_id
    ).all()
    for bill in overdue_bills:
        notifications.append(f"Geciken fatura: {bill.description} - {bill.due_date.strftime('%d.%m.%Y')}")
    # Yaklaşan giderler
    upcoming_expenses = Expense.query.filter(
        Expense.date.between(today, next_week),
        Expense.member_id == member_id
    ).all()
    for exp in upcoming_expenses:
        notifications.append(f"Yaklaşan gider: {exp.description} - {exp.date.strftime('%d.%m.%Y')}")
    # Son eklenen önemli dosyalar (son 3 gün)
    from datetime import datetime, timedelta as td
    three_days_ago = datetime.now() - td(days=3)
    new_files = ImportantFile.query.filter(
        ImportantFile.member_id == member_id,
        ImportantFile.upload_date >= three_days_ago
    ).all()
    for f in new_files:
        notifications.append(f"Yeni dosya: {f.filename}")
    return notifications[:5]

@app.context_processor
def inject_notifications():
    return dict(notifications=get_notifications())

@app.route('/customer_detail/<int:customer_id>')
def customer_detail(customer_id):
    customer = Customer.query.filter_by(id=customer_id, member_id=session['member_id']).first_or_404()
    sales = Sale.query.filter_by(customer_id=customer_id, member_id=session['member_id']).order_by(Sale.sale_date.desc()).all()
    bills = Bill.query.filter_by(member_id=session['member_id']).all()  # Faturalar müşteriyle ilişkiliyse burada filtrelenmeli
    # Eğer Bill modelinde customer_id yoksa, sadece satışlar gösterilecek
    return render_template('customer_detail.html', customer=customer, sales=sales, bills=bills)

@app.route('/edit_sale/<int:sale_id>', methods=['GET', 'POST'])
def edit_sale(sale_id):
    sale = Sale.query.filter_by(id=sale_id, member_id=session['member_id']).first_or_404()
    if request.method == 'POST':
        sale.customer_id = int(request.form['customer_id'])
        sale.package_id = int(request.form['package_id'])
        sale.sale_date = datetime.strptime(request.form['sale_date'], '%Y-%m-%d').date()
        sale.amount = float(request.form['amount'])
        sale.payment_type = request.form['payment_type']
        sale.notes = request.form.get('notes')
        db.session.commit()
        flash('Satış başarıyla güncellendi!', 'success')
        return redirect(url_for('sales'))
    customers = Customer.query.filter_by(member_id=session['member_id']).all()
    packages = SalesPackage.query.filter_by(member_id=session['member_id']).all()
    payment_types = ['Kredi Kartı', 'Nakit', 'Havale/EFT', 'Çek', 'Senet', 'Vadeli Ödeme']
    return render_template('edit_sale.html', sale=sale, customers=customers, packages=packages, payment_types=payment_types)

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, member_id=session['member_id']).first_or_404()
    if request.method == 'POST':
        expense.description = request.form['description']
        expense.amount = float(request.form['amount'])
        expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        expense.category = request.form.get('category')
        customer_id = request.form.get('customer_id')
        if customer_id and customer_id != '':
            expense.customer_id = int(customer_id)
        else:
            expense.customer_id = None
        db.session.commit()
        flash('Gider başarıyla güncellendi!', 'success')
        return redirect(url_for('expenses'))
    customers = Customer.query.filter_by(member_id=session['member_id']).order_by(Customer.name.asc()).all()
    return render_template('edit_expense.html', expense=expense, customers=customers)

@app.route('/edit_bill/<int:bill_id>', methods=['GET', 'POST'])
def edit_bill(bill_id):
    bill = Bill.query.filter_by(id=bill_id, member_id=session['member_id']).first_or_404()
    if request.method == 'POST':
        bill.description = request.form['description']
        bill.amount = float(request.form['amount'])
        bill.due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d').date()
        bill.status = request.form['status']
        db.session.commit()
        flash('Fatura başarıyla güncellendi!', 'success')
        return redirect(url_for('bills'))
    return render_template('edit_bill.html', bill=bill)

@app.route('/edit_investment/<int:investment_id>', methods=['GET', 'POST'])
def edit_investment(investment_id):
    investment = Investment.query.filter_by(id=investment_id, member_id=session['member_id']).first_or_404()
    if request.method == 'POST':
        investment.name = request.form['name']
        investment.type = request.form.get('type')
        investment.amount_invested = float(request.form['amount_invested'])
        investment.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
        current_value = request.form.get('current_value')
        investment.current_value = float(current_value) if current_value else None
        db.session.commit()
        flash('Yatırım başarıyla güncellendi!', 'success')
        return redirect(url_for('investments'))
    return render_template('edit_investment.html', investment=investment)

@app.route('/bank_accounts', methods=['GET', 'POST'])
def bank_accounts():
    member_id = session.get('member_id')
    if not member_id:
        return redirect(url_for('login'))
    if request.method == 'POST':
        account_name = request.form['account_name']
        bank_name = request.form['bank_name']
        account_number = request.form['account_number']
        iban = request.form['iban']
        balance = float(request.form.get('balance', 0))
        db.session.add(BankAccount(member_id=member_id, account_name=account_name, bank_name=bank_name, account_number=account_number, iban=iban, balance=balance))
        db.session.commit()
        flash('Banka hesabı başarıyla eklendi!', 'success')
        return redirect(url_for('bank_accounts'))
    accounts = BankAccount.query.filter_by(member_id=member_id).all()
    return render_template('bank_accounts.html', accounts=accounts)

@app.route('/bank_transaction_in/<int:account_id>', methods=['POST'])
def bank_transaction_in(account_id):
    member_id = session.get('member_id')
    account = BankAccount.query.filter_by(id=account_id, member_id=member_id).first_or_404()
    amount = float(request.form['amount'])
    description = request.form.get('description', '')
    # İşlem kaydı
    transaction = BankTransaction(bank_account_id=account.id, type='in', amount=amount, description=description)
    db.session.add(transaction)
    # Bakiye güncelle
    account.balance += amount
    db.session.commit()
    flash('Para başarıyla eklendi.', 'success')
    return redirect(url_for('bank_accounts'))

@app.route('/bank_transaction_out/<int:account_id>', methods=['POST'])
def bank_transaction_out(account_id):
    member_id = session.get('member_id')
    account = BankAccount.query.filter_by(id=account_id, member_id=member_id).first_or_404()
    amount = float(request.form['amount'])
    description = request.form.get('description', '')
    # Negatif bakiyeye izin verme
    if account.balance < amount:
        flash('Yetersiz bakiye!', 'danger')
        return redirect(url_for('bank_accounts'))
    from src.models.finance_models import BankTransaction
    transaction = BankTransaction(bank_account_id=account.id, type='out', amount=amount, description=description)
    db.session.add(transaction)
    account.balance -= amount
    db.session.commit()
    flash('Para başarıyla gönderildi.', 'success')
    return redirect(url_for('bank_accounts'))

@app.route('/delete_bank_account/<int:account_id>', methods=['POST'])
def delete_bank_account(account_id):
    account = BankAccount.query.get_or_404(account_id)
    db.session.delete(account)
    db.session.commit()
    flash('Banka hesabı silindi.', 'success')
    return redirect(url_for('bank_accounts'))

@app.route('/edit_bank_account/<int:account_id>', methods=['GET', 'POST'])
def edit_bank_account(account_id):
    member_id = session.get('member_id')
    if not member_id:
        return redirect(url_for('login'))
    account = BankAccount.query.filter_by(id=account_id, member_id=member_id).first_or_404()
    if request.method == 'POST':
        account.account_name = request.form['account_name']
        account.bank_name = request.form['bank_name']
        account.account_number = request.form['account_number']
        account.iban = request.form['iban']
        db.session.commit()
        flash('Banka hesabı başarıyla güncellendi!', 'success')
        return redirect(url_for('bank_accounts'))
    return render_template('edit_bank_account.html', account=account)

def get_currency_rates():
    rates = {'usd': '-', 'eur': '-', 'gbp': '-', 'btc': '-', 'gold': '-'}
    try:
        usd = requests.get('https://doviz.dev/v1/usd.json', timeout=5)
        print('USD API yanıtı:', usd.text)
        usd = usd.json()
        rates['usd'] = f"{usd.get('USDTRY', '-'):.2f}" if 'USDTRY' in usd else '-'
        # Diğerleri aynı şekilde...
    except Exception as e:
        print('Döviz çekme hatası:', e)
    return rates

@app.before_request
def inject_currency_rates():
    g.currency_rates = get_currency_rates()

@app.route('/api/customers/search')
def api_customers_search():
    query = request.args.get('q', '').strip()
    base_query = Customer.query.filter_by(member_id=session['member_id'])
    if query:
        customers = base_query.filter(Customer.name.ilike(f'%{query}%')).all()
    else:
        customers = base_query.all()
    result = [
        {
            'id': c.id,
            'name': c.name,
            'email': c.email,
            'phone': c.phone,
            'address': c.address,
            'iban': c.iban or ''
        } for c in customers
    ]
    return jsonify(result)

@app.route('/api/sales_packages/search')
def api_sales_packages_search():
    query = request.args.get('q', '').strip()
    base_query = SalesPackage.query.filter_by(member_id=session['member_id'])
    if query:
        packages = base_query.filter(SalesPackage.name.ilike(f'%{query}%')).all()
    else:
        packages = base_query.all()
    result = [
        {
            'id': p.id,
            'name': p.name,
            'description': p.description or '',
            'price': p.price,
            'category': p.category or ''
        } for p in packages
    ]
    return jsonify(result)

@app.route('/api/sales/search')
def api_sales_search():
    query = request.args.get('q', '').strip()
    base_query = Sale.query.filter_by(member_id=session['member_id'])
    if query:
        sales = base_query.join(Customer).filter(Customer.name.ilike(f'%{query}%')).all()
    else:
        sales = base_query.all()
    result = [
        {
            'id': s.id,
            'customer_name': s.customer.name if s.customer else '',
            'package_name': s.package.name if s.package else '',
            'sale_date': s.sale_date.strftime('%Y-%m-%d'),
            'amount': s.amount,
            'payment_type': s.payment_type,
            'notes': s.notes or ''
        } for s in sales
    ]
    return jsonify(result)

@app.route('/api/incomes/search')
def api_incomes_search():
    query = request.args.get('q', '').strip()
    base_query = Income.query.filter_by(member_id=session['member_id'])
    if query:
        incomes = base_query.filter(Income.description.ilike(f'%{query}%')).all()
    else:
        incomes = base_query.all()
    result = [
        {
            'id': i.id,
            'description': i.description,
            'amount': i.amount,
            'date': i.date.strftime('%Y-%m-%d'),
            'category': i.category or ''
        } for i in incomes
    ]
    return jsonify(result)

@app.route('/api/expenses/search')
def api_expenses_search():
    query = request.args.get('q', '').strip()
    base_query = Expense.query.filter_by(member_id=session['member_id'])
    if query:
        expenses = base_query.filter(Expense.description.ilike(f'%{query}%')).all()
    else:
        expenses = base_query.all()
    result = [
        {
            'id': e.id,
            'description': e.description,
            'amount': e.amount,
            'date': e.date.strftime('%Y-%m-%d'),
            'category': e.category or ''
        } for e in expenses
    ]
    return jsonify(result)

@app.route('/api/bills/search')
def api_bills_search():
    query = request.args.get('q', '').strip()
    base_query = Bill.query.filter_by(member_id=session['member_id'])
    if query:
        bills = base_query.filter(Bill.description.ilike(f'%{query}%')).all()
    else:
        bills = base_query.all()
    result = [
        {
            'id': b.id,
            'description': b.description,
            'amount': b.amount,
            'due_date': b.due_date.strftime('%Y-%m-%d'),
            'status': b.status
        } for b in bills
    ]
    return jsonify(result)

@app.route('/account_transactions/<int:account_id>')
def account_transactions(account_id):
    member_id = session.get('member_id')
    if not member_id:
        return redirect(url_for('login'))
    account = BankAccount.query.filter_by(id=account_id, member_id=member_id).first_or_404()
    transactions = BankTransaction.query.filter_by(bank_account_id=account.id).order_by(BankTransaction.date.desc()).all()
    return render_template('account_transactions.html', account=account, transactions=transactions)

# Kripto Cüzdanları Modeli (varsa import edilir, yoksa eklenmeli)
from sqlalchemy import Column, Integer, String, Float

class CryptoWallet(db.Model):
    __tablename__ = 'crypto_wallets'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    wallet_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='USDT')

@app.route('/crypto_wallets', methods=['GET', 'POST'])
def crypto_wallets():
    member_id = session.get('member_id')
    if not member_id:
        return redirect(url_for('login'))
    if request.method == 'POST':
        wallet_name = request.form['wallet_name']
        address = request.form['address']
        balance = float(request.form.get('balance', 0))
        currency = request.form.get('currency', 'USDT')
        db.session.add(CryptoWallet(member_id=member_id, wallet_name=wallet_name, address=address, balance=balance, currency=currency))
        db.session.commit()
        flash('Kripto cüzdanı başarıyla eklendi!', 'success')
        return redirect(url_for('crypto_wallets'))
    wallets = CryptoWallet.query.filter_by(member_id=member_id).all()
    return render_template('crypto_wallets.html', wallets=wallets)

@app.route('/delete_crypto_wallet/<int:wallet_id>', methods=['POST'])
def delete_crypto_wallet(wallet_id):
    member_id = session.get('member_id')
    wallet = CryptoWallet.query.filter_by(id=wallet_id, member_id=member_id).first_or_404()
    db.session.delete(wallet)
    db.session.commit()
    flash('Kripto cüzdanı silindi.', 'success')
    return redirect(url_for('crypto_wallets'))

@app.route('/export_pdf')
def export_pdf():
    import pdfkit
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    # Raporlar için mevcut filtreleri al
    member_id = session.get('member_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    tx_type = request.args.get('type', 'all')
    category = request.args.get('category', 'all')
    # Kategoriler
    all_categories = sorted(set([e.category for e in Expense.query.filter_by(member_id=member_id) if e.category] + [i.category for i in Income.query.filter_by(member_id=member_id) if i.category]))
    # Filtreli işlemler
    income_query = Income.query.filter_by(member_id=member_id)
    expense_query = Expense.query.filter_by(member_id=member_id)
    if start_date:
        income_query = income_query.filter(Income.date >= start_date)
        expense_query = expense_query.filter(Expense.date >= start_date)
    if end_date:
        income_query = income_query.filter(Income.date <= end_date)
        expense_query = expense_query.filter(Expense.date <= end_date)
    if category != 'all':
        income_query = income_query.filter(Income.category == category)
        expense_query = expense_query.filter(Expense.category == category)
    if tx_type == 'income':
        expense_query = expense_query.filter(Expense.id == -1)  # Boş
    elif tx_type == 'expense':
        income_query = income_query.filter(Income.id == -1)  # Boş
    incomes = income_query.all() or []
    expenses = expense_query.all() or []
    # Özetler
    total_income = sum(i.amount for i in incomes) if incomes else 0.0
    total_expenses = sum(e.amount for e in expenses) if expenses else 0.0
    net_savings = total_income - total_expenses
    # Kategori bazlı özet
    category_summary = []
    all_items = []
    for i in incomes:
        all_items.append({'category': i.category or 'Diğer', 'type': 'income', 'amount': i.amount})
    for e in expenses:
        all_items.append({'category': e.category or 'Diğer', 'type': 'expense', 'amount': e.amount})
    from collections import defaultdict
    cat_groups = {}
    for item in all_items:
        key = (item['category'], item['type'])
        if key not in cat_groups:
            cat_groups[key] = {'category': item['category'], 'type': item['type'], 'count': 0, 'total': 0.0}
        cat_groups[key]['count'] += 1
        cat_groups[key]['total'] += item['amount']
    total_all = sum(x['total'] for x in cat_groups.values()) or 1
    for v in cat_groups.values():
        v['percent'] = 100 * v['total'] / total_all
        category_summary.append(v)
    category_summary = sorted(category_summary, key=lambda x: -x['total'])
    rendered = render_template('reports_pdf.html',
        total_income=total_income,
        total_expenses=total_expenses,
        net_savings=net_savings,
        category_summary=category_summary,
        start_date=start_date,
        end_date=end_date,
        category=category,
        tx_type=tx_type
    )
    pdf = pdfkit.from_string(rendered, False, configuration=config)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=rapor.pdf'
    return response

if __name__ == '__main__':
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'templates')):
        os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'))
    print(">>> main.py ÇALIŞIYOR <<<")
    app.run(host='0.0.0.0', port=5000, debug=True)
