from src.models.db import db

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    member = db.relationship('Member', backref=db.backref('incomes', lazy=True))

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    member = db.relationship('Member', backref=db.backref('expenses', lazy=True))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    customer = db.relationship('Customer', backref=db.backref('expenses', lazy=True))

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Unpaid') # e.g., Unpaid, Paid, Overdue
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    member = db.relationship('Member', backref=db.backref('bills', lazy=True))

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(100), nullable=True) # e.g., Stocks, Bonds, Real Estate
    amount_invested = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, nullable=True)
    purchase_date = db.Column(db.Date, nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    member = db.relationship('Member', backref=db.backref('investments', lazy=True))

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(250), nullable=True)
    iban = db.Column(db.String(34), nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    member = db.relationship('Member', backref=db.backref('customers', lazy=True))
    # Add other customer-related fields as needed

class SalesPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    member = db.relationship('Member', backref=db.backref('sales_packages', lazy=True))
    # Add other package-related fields as needed

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('sales_package.id'), nullable=False)
    sale_date = db.Column(db.Date, nullable=False, default=db.func.current_date())
    amount = db.Column(db.Float, nullable=False) # Could be different from package price if discounts apply
    payment_type = db.Column(db.String(50), nullable=False) # e.g., Credit Card, Cash, Bank Transfer, Check, Promissory Note, Installment
    notes = db.Column(db.Text, nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    member = db.relationship('Member', backref=db.backref('sales', lazy=True))
    customer = db.relationship('Customer', backref=db.backref('sales', lazy=True))
    package = db.relationship('SalesPackage', backref=db.backref('sales', lazy=True))

class ImportantFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    member = db.relationship('Member', backref=db.backref('important_files', lazy=True))

class BankAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=True)
    iban = db.Column(db.String(34), nullable=True)
    balance = db.Column(db.Float, nullable=False, default=0.0)
    member = db.relationship('Member', backref=db.backref('bank_accounts', lazy=True))

class BankTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'in' veya 'out'
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    date = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    bank_account = db.relationship('BankAccount', backref=db.backref('transactions', lazy=True))

