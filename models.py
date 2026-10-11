from datetime import datetime, date
from zoneinfo import ZoneInfo
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

MANILA_TZ = ZoneInfo("Asia/Manila")

def manila_now():
    return datetime.now(MANILA_TZ)

def manila_today():
    return datetime.now(MANILA_TZ).date()

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), default='Administrator')
    created_at = db.Column(db.DateTime, default=manila_now)

    def __init__(self, username=None, full_name='Administrator', **kwargs):
        super().__init__(**kwargs)
        if username:
            self.username = username
        self.full_name = full_name

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.username}>'


class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(50), unique=True, nullable=False)
    capacity = db.Column(db.Integer, default=1, nullable=False)
    monthly_rent = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='Available')  # 'Available', 'Occupied', 'Maintenance'
    created_at = db.Column(db.DateTime, default=manila_now)

    # Relationships
    tenants = db.relationship('Tenant', backref='room', lazy=True)
    maintenance_requests = db.relationship('MaintenanceRequest', backref='room', lazy=True)

    def __init__(self, room_number=None, capacity=1, monthly_rent=0.0, description=None, status='Available', **kwargs):
        super().__init__(**kwargs)
        if room_number is not None:
            self.room_number = room_number
        self.capacity = int(capacity) if capacity else 1
        self.monthly_rent = float(monthly_rent) if monthly_rent else 0.0
        self.description = description
        self.status = status

    @property
    def active_tenants(self):
        return [t for t in self.tenants if t.status == 'Active']

    @property
    def active_tenants_count(self):
        return len(self.active_tenants)

    @property
    def is_full(self):
        return self.active_tenants_count >= self.capacity

    @property
    def available_slots(self):
        return max(0, self.capacity - self.active_tenants_count)

    def update_occupancy_status(self):
        """Automatically adjust status if full or empty (unless in Maintenance)"""
        if self.status != 'Maintenance':
            if self.is_full:
                self.status = 'Occupied'
            else:
                self.status = 'Available'

    def __repr__(self):
        return f'<Room {self.room_number}>'


class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=False)
    emergency_contact = db.Column(db.String(120), nullable=True)
    move_in_date = db.Column(db.Date, nullable=False, default=manila_today)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    status = db.Column(db.String(20), default='Active')  # 'Active', 'Moved Out'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=manila_now)

    # Relationships
    payments = db.relationship('Payment', backref='tenant', lazy=True, cascade='all, delete-orphan')
    maintenance_requests = db.relationship('MaintenanceRequest', backref='tenant', lazy=True)

    def __init__(self, full_name=None, phone=None, email=None, emergency_contact=None, move_in_date=None, room_id=None, status='Active', notes=None, **kwargs):
        super().__init__(**kwargs)
        if full_name:
            self.full_name = full_name
        if phone:
            self.phone = phone
        self.email = email
        self.emergency_contact = emergency_contact
        self.move_in_date = move_in_date if move_in_date else manila_today()
        self.room_id = room_id
        self.status = status
        self.notes = notes

    @property
    def total_paid(self):
        return sum(p.amount_paid for p in self.payments if p.status == 'Paid')

    @property
    def total_unpaid(self):
        return sum(p.amount_paid for p in self.payments if p.status in ('Overdue', 'Partial'))

    def __repr__(self):
        return f'<Tenant {self.full_name}>'


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=manila_today)
    due_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50), default='Cash')  # 'Cash', 'GCash', 'Bank Transfer', 'Other'
    status = db.Column(db.String(20), default='Paid')  # 'Paid', 'Partial', 'Overdue'
    reference_number = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=manila_now)

    def __init__(self, tenant_id=None, amount_paid=0.0, payment_date=None, due_date=None, payment_method='Cash', status='Paid', reference_number=None, notes=None, **kwargs):
        super().__init__(**kwargs)
        self.tenant_id = tenant_id
        self.amount_paid = float(amount_paid) if amount_paid else 0.0
        self.payment_date = payment_date if payment_date else manila_today()
        self.due_date = due_date if due_date else manila_today()
        self.payment_method = payment_method
        self.status = status
        self.reference_number = reference_number
        self.notes = notes

    def __repr__(self):
        return f'<Payment {self.id} - ₱{self.amount_paid}>'


class MaintenanceRequest(db.Model):
    __tablename__ = 'maintenance_requests'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='Medium')  # 'Low', 'Medium', 'High', 'Urgent'
    status = db.Column(db.String(30), default='Pending')    # 'Pending', 'In Progress', 'Resolved'
    cost = db.Column(db.Float, default=0.0)
    reported_date = db.Column(db.Date, default=manila_today)
    resolved_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=manila_now)

    def __init__(self, room_id=None, tenant_id=None, title=None, description=None, priority='Medium', status='Pending', cost=0.0, reported_date=None, resolved_date=None, **kwargs):
        super().__init__(**kwargs)
        self.room_id = room_id
        self.tenant_id = tenant_id
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status
        self.cost = float(cost) if cost else 0.0
        self.reported_date = reported_date if reported_date else manila_today()
        self.resolved_date = resolved_date

    def __repr__(self):
        return f'<MaintenanceRequest {self.title} - {self.status}>'
