from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from config import Config
from models import db, Admin, Room, Tenant, Payment, MaintenanceRequest

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize SQLite database with Flask
    db.init_app(app)

    # Ensure tables exist and create initial admin account
    with app.app_context():
        db.create_all()
        # Seed default admin user if none exists
        if not Admin.query.first():
            default_admin = Admin(
                username='admin',
                full_name='Super Administrator'
            )
            default_admin.set_password('admin123')
            db.session.add(default_admin)
            db.session.commit()
            print(">> Default admin account created: username 'admin', password 'admin123'")

    # Authentication decorator
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                flash('Please sign in to access the system.', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    # -------------------------------------------------------------
    # Authentication Routes
    # -------------------------------------------------------------
    @app.route('/')
    def index():
        if 'admin_id' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'admin_id' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            admin = Admin.query.filter_by(username=username).first()
            if admin and admin.check_password(password):
                session['admin_id'] = admin.id
                session['admin_name'] = admin.full_name
                flash(f'Welcome back, {admin.full_name}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password. Please try again.', 'error')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been successfully logged out.', 'info')
        return redirect(url_for('login'))

    # -------------------------------------------------------------
    # Dashboard Route
    # -------------------------------------------------------------
    @app.route('/dashboard')
    @login_required
    def dashboard():
        total_rooms = Room.query.count()
        available_rooms = Room.query.filter_by(status='Available').count()
        active_tenants = Tenant.query.filter_by(status='Active').count()
        
        # Calculate overall occupancy percentage based on room capacities
        all_rooms = Room.query.all()
        total_capacity = sum(r.capacity for r in all_rooms) if all_rooms else 0
        occupancy_rate = round((active_tenants / total_capacity * 100), 1) if total_capacity > 0 else 0
        
        # Sum total revenue
        paid_payments = Payment.query.filter_by(status='Paid').all()
        total_revenue = sum(p.amount_paid for p in paid_payments)

        return render_template(
            'dashboard.html',
            active_page='dashboard',
            total_rooms=total_rooms,
            available_rooms=available_rooms,
            active_tenants=active_tenants,
            occupancy_rate=occupancy_rate,
            total_revenue=total_revenue
        )

    # -------------------------------------------------------------
    # Placeholders for Next Implementation Steps
    # -------------------------------------------------------------
    @app.route('/rooms')
    @login_required
    def rooms():
        return redirect(url_for('dashboard'))

    @app.route('/tenants')
    @login_required
    def tenants():
        return redirect(url_for('dashboard'))

    @app.route('/payments')
    @login_required
    def payments():
        return redirect(url_for('dashboard'))

    @app.route('/maintenance')
    @login_required
    def maintenance():
        return redirect(url_for('dashboard'))

    @app.route('/reports')
    @login_required
    def reports():
        return redirect(url_for('dashboard'))

    return app


app = create_app()

if __name__ == '__main__':
    # Run development server on port 5000
    app.run(debug=True, host='127.0.0.1', port=5000)
