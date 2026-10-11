from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), default='Administrator')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tenants = db.relationship('Tenant', backref='room', lazy=True)
    maintenance_requests = db.relationship('MaintenanceRequest', backref='room', lazy=True)

    @property
    def active_tenants_count(self):
        return sum(1 for t in self.tenants if t.status == 'Active')

    @property
    def is_full(self):
        return self.active_tenants_count >= self.capacity

    @property
    def available_slots(self):
        return max(0, self.capacity - self.active_tenants_count)

    def __repr__(self):
        return f'<Room {self.room_number}>'


class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=False)
    emergency_contact = db.Column(db.String(120), nullable=True)
    move_in_date = db.Column(db.Date, nullable=False, default=date.today)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    status = db.Column(db.String(20), default='Active')  # 'Active', 'Moved Out'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    payments = db.relationship('Payment', backref='tenant', lazy=True, cascade='all, delete-orphan')
    maintenance_requests = db.relationship('MaintenanceRequest', backref='tenant', lazy=True)

    @property
    def total_paid(self):
        return sum(p.amount_paid for p in self.payments if p.status == 'Paid')

    def __repr__(self):
        return f'<Tenant {self.full_name}>'


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50), default='Cash')  # 'Cash', 'GCash', 'Bank Transfer', 'Other'
    status = db.Column(db.String(20), default='Paid')  # 'Paid', 'Partial', 'Overdue'
    reference_number = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    reported_date = db.Column(db.Date, default=date.today)
    resolved_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MaintenanceRequest {self.title} - {self.status}>'
