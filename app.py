import os
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from config import Config
from models import db, Admin, Room, Tenant, Payment, MaintenanceRequest, manila_today, manila_now

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize SQLite database
    db.init_app(app)

    # Initialize tables and seed default admin
    with app.app_context():
        db.create_all()
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
                flash('Please sign in to access the management portal.', 'warning')
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
                flash('Invalid admin username or password. Please try again.', 'error')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out successfully.', 'info')
        return redirect(url_for('login'))

    # -------------------------------------------------------------
    # Admin Dashboard
    # -------------------------------------------------------------
    @app.route('/dashboard')
    @login_required
    def dashboard():
        total_rooms = Room.query.count()
        available_rooms = Room.query.filter_by(status='Available').count()
        active_tenants = Tenant.query.filter_by(status='Active').count()

        all_rooms = Room.query.all()
        total_capacity = sum(r.capacity for r in all_rooms) if all_rooms else 0
        total_occupied = sum(r.active_tenants_count for r in all_rooms) if all_rooms else 0
        available_slots = max(0, total_capacity - total_occupied)
        occupancy_rate = round((total_occupied / total_capacity * 100), 1) if total_capacity > 0 else 0

        paid_payments = Payment.query.filter_by(status='Paid').all()
        total_revenue = sum(p.amount_paid for p in paid_payments)

        # Recent 5 payments
        recent_payments = Payment.query.order_by(Payment.payment_date.desc(), Payment.id.desc()).limit(5).all()

        # Recent 5 pending / in-progress maintenance requests
        pending_maintenance = MaintenanceRequest.query.filter(MaintenanceRequest.status != 'Resolved')\
            .order_by(MaintenanceRequest.created_at.desc()).limit(5).all()

        return render_template(
            'dashboard.html',
            active_page='dashboard',
            total_rooms=total_rooms,
            available_rooms=available_rooms,
            active_tenants=active_tenants,
            available_slots=available_slots,
            occupancy_rate=occupancy_rate,
            total_revenue=total_revenue,
            recent_payments=recent_payments,
            pending_maintenance=pending_maintenance
        )

    # -------------------------------------------------------------
    # Room Management Routes
    # -------------------------------------------------------------
    @app.route('/rooms')
    @login_required
    def rooms():
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()

        query = Room.query
        if search:
            query = query.filter(Room.room_number.ilike(f'%{search}%'))
        if status_filter:
            query = query.filter_by(status=status_filter)

        rooms_list = query.order_by(Room.room_number.asc()).all()
        return render_template(
            'rooms/index.html',
            active_page='rooms',
            rooms=rooms_list,
            search=search,
            status_filter=status_filter
        )

    @app.route('/rooms/add', methods=['GET', 'POST'])
    @login_required
    def rooms_add():
        if request.method == 'POST':
            room_number = request.form.get('room_number', '').strip()
            capacity_raw = request.form.get('capacity', '1')
            rent_raw = request.form.get('monthly_rent', '0')
            description = request.form.get('description', '').strip()
            status = request.form.get('status', 'Available')

            # Validation
            if not room_number:
                flash('Room number or name is required.', 'error')
                return render_template('rooms/form.html', active_page='rooms', room=None)

            if Room.query.filter_by(room_number=room_number).first():
                flash(f'Room "{room_number}" already exists. Please choose a unique room name.', 'error')
                return render_template('rooms/form.html', active_page='rooms', room=None)

            try:
                capacity = int(capacity_raw)
                monthly_rent = float(rent_raw)
                if capacity < 1:
                    raise ValueError("Capacity must be at least 1.")
                if monthly_rent < 0:
                    raise ValueError("Rent cannot be negative.")
            except ValueError as e:
                flash(f'Invalid input: {str(e)}', 'error')
                return render_template('rooms/form.html', active_page='rooms', room=None)

            new_room = Room(
                room_number=room_number,
                capacity=capacity,
                monthly_rent=monthly_rent,
                description=description,
                status=status
            )
            db.session.add(new_room)
            db.session.commit()

            flash(f'Room "{room_number}" added successfully!', 'success')
            return redirect(url_for('rooms'))

        return render_template('rooms/form.html', active_page='rooms', room=None)

    @app.route('/rooms/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def rooms_edit(id):
        room = Room.query.get_or_404(id)

        if request.method == 'POST':
            room_number = request.form.get('room_number', '').strip()
            capacity_raw = request.form.get('capacity', '1')
            rent_raw = request.form.get('monthly_rent', '0')
            description = request.form.get('description', '').strip()
            status = request.form.get('status', room.status)

            if not room_number:
                flash('Room number or name is required.', 'error')
                return render_template('rooms/form.html', active_page='rooms', room=room)

            # Check duplicate room number
            existing = Room.query.filter_by(room_number=room_number).first()
            if existing and existing.id != room.id:
                flash(f'Another room already exists with number "{room_number}".', 'error')
                return render_template('rooms/form.html', active_page='rooms', room=room)

            try:
                capacity = int(capacity_raw)
                monthly_rent = float(rent_raw)
                if capacity < 1:
                    raise ValueError("Capacity must be at least 1.")
                if monthly_rent < 0:
                    raise ValueError("Rent cannot be negative.")
            except ValueError as e:
                flash(f'Invalid input: {str(e)}', 'error')
                return render_template('rooms/form.html', active_page='rooms', room=room)

            room.room_number = room_number
            room.capacity = capacity
            room.monthly_rent = monthly_rent
            room.description = description
            room.status = status
            room.update_occupancy_status()

            db.session.commit()
            flash(f'Room "{room.room_number}" updated successfully.', 'success')
            return redirect(url_for('rooms'))

        return render_template('rooms/form.html', active_page='rooms', room=room)

    @app.route('/rooms/view/<int:id>')
    @login_required
    def rooms_view(id):
        room = Room.query.get_or_404(id)
        return render_template('rooms/view.html', active_page='rooms', room=room)

    @app.route('/rooms/delete/<int:id>', methods=['POST'])
    @login_required
    def rooms_delete(id):
        room = Room.query.get_or_404(id)

        # Check for active occupants
        if room.active_tenants_count > 0:
            flash(f'Cannot delete Room "{room.room_number}" because it currently has {room.active_tenants_count} active tenant(s). Please move out or reassign them first.', 'error')
            return redirect(url_for('rooms'))

        db.session.delete(room)
        db.session.commit()
        flash(f'Room "{room.room_number}" was successfully deleted.', 'success')
        return redirect(url_for('rooms'))

    # -------------------------------------------------------------
    # Tenant Management Routes
    # -------------------------------------------------------------
    @app.route('/tenants')
    @login_required
    def tenants():
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()

        query = Tenant.query
        if search:
            query = query.filter(
                (Tenant.full_name.ilike(f'%{search}%')) |
                (Tenant.phone.ilike(f'%{search}%'))
            )
        if status_filter:
            query = query.filter_by(status=status_filter)

        tenants_list = query.order_by(Tenant.status.asc(), Tenant.full_name.asc()).all()
        return render_template(
            'tenants/index.html',
            active_page='tenants',
            tenants=tenants_list,
            search=search,
            status_filter=status_filter
        )

    @app.route('/tenants/add', methods=['GET', 'POST'])
    @login_required
    def tenants_add():
        available_rooms = Room.query.order_by(Room.room_number.asc()).all()

        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip() or None
            emergency_contact = request.form.get('emergency_contact', '').strip() or None
            room_id_raw = request.form.get('room_id', '')
            move_in_str = request.form.get('move_in_date', '')
            status = request.form.get('status', 'Active')
            notes = request.form.get('notes', '').strip() or None

            if not full_name or not phone:
                flash('Full name and phone number are required.', 'error')
                return render_template('tenants/form.html', active_page='tenants', tenant=None, rooms=available_rooms, today=manila_today().isoformat())

            # Parse move-in date
            try:
                move_in_date = datetime.strptime(move_in_str, '%Y-%m-%d').date() if move_in_str else manila_today()
            except ValueError:
                move_in_date = manila_today()

            room_id = int(room_id_raw) if room_id_raw and room_id_raw.isdigit() else None
            
            # Check room capacity if a room was assigned
            if room_id and status == 'Active':
                target_room = db.session.get(Room, room_id)
                if target_room and target_room.is_full:
                    flash(f'Room "{target_room.room_number}" is currently full (Capacity: {target_room.capacity}). Please select another room.', 'error')
                    return render_template('tenants/form.html', active_page='tenants', tenant=None, rooms=available_rooms, today=manila_today().isoformat())

            new_tenant = Tenant(
                full_name=full_name,
                phone=phone,
                email=email,
                emergency_contact=emergency_contact,
                move_in_date=move_in_date,
                room_id=room_id,
                status=status,
                notes=notes
            )
            db.session.add(new_tenant)
            db.session.commit()

            # Update assigned room status
            if room_id:
                target_room = db.session.get(Room, room_id)
                if target_room:
                    target_room.update_occupancy_status()
                    db.session.commit()

            flash(f'Tenant "{full_name}" registered successfully!', 'success')
            return redirect(url_for('tenants'))

        return render_template('tenants/form.html', active_page='tenants', tenant=None, rooms=available_rooms, today=manila_today().isoformat())

    @app.route('/tenants/view/<int:id>')
    @login_required
    def tenants_view(id):
        tenant = Tenant.query.get_or_404(id)
        return render_template('tenants/view.html', active_page='tenants', tenant=tenant)

    @app.route('/tenants/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def tenants_edit(id):
        tenant = Tenant.query.get_or_404(id)
        available_rooms = Room.query.order_by(Room.room_number.asc()).all()

        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip() or None
            emergency_contact = request.form.get('emergency_contact', '').strip() or None
            room_id_raw = request.form.get('room_id', '')
            move_in_str = request.form.get('move_in_date', '')
            status = request.form.get('status', 'Active')
            notes = request.form.get('notes', '').strip() or None

            if not full_name or not phone:
                flash('Full name and phone number are required.', 'error')
                return render_template('tenants/form.html', active_page='tenants', tenant=tenant, rooms=available_rooms, today=manila_today().isoformat())

            try:
                move_in_date = datetime.strptime(move_in_str, '%Y-%m-%d').date() if move_in_str else tenant.move_in_date
            except ValueError:
                move_in_date = tenant.move_in_date

            old_room_id = tenant.room_id
            new_room_id = int(room_id_raw) if room_id_raw and room_id_raw.isdigit() else None

            # If room changed and new room is selected, check capacity
            if new_room_id and new_room_id != old_room_id and status == 'Active':
                target_room = db.session.get(Room, new_room_id)
                if target_room and target_room.is_full:
                    flash(f'Room "{target_room.room_number}" is currently full. Please pick an available room.', 'error')
                    return render_template('tenants/form.html', active_page='tenants', tenant=tenant, rooms=available_rooms, today=manila_today().isoformat())

            tenant.full_name = full_name
            tenant.phone = phone
            tenant.email = email
            tenant.emergency_contact = emergency_contact
            tenant.move_in_date = move_in_date
            tenant.room_id = new_room_id
            tenant.status = status
            tenant.notes = notes

            db.session.commit()

            # Update previous room & new room status
            if old_room_id:
                old_room = db.session.get(Room, old_room_id)
                if old_room:
                    old_room.update_occupancy_status()
            if new_room_id:
                new_room = db.session.get(Room, new_room_id)
                if new_room:
                    new_room.update_occupancy_status()
            db.session.commit()

            flash(f'Tenant "{tenant.full_name}" details updated successfully.', 'success')
            return redirect(url_for('tenants_view', id=tenant.id))

        return render_template('tenants/form.html', active_page='tenants', tenant=tenant, rooms=available_rooms, today=manila_today().isoformat())

    @app.route('/tenants/checkout/<int:id>', methods=['POST'])
    @login_required
    def tenants_checkout(id):
        tenant = Tenant.query.get_or_404(id)
        room_id = tenant.room_id

        tenant.status = 'Moved Out'
        tenant.room_id = None
        db.session.commit()

        if room_id:
            room = db.session.get(Room, room_id)
            if room:
                room.update_occupancy_status()
                db.session.commit()

        flash(f'Tenant "{tenant.full_name}" was checked out. Room slot is now freed up.', 'info')
        return redirect(url_for('tenants_view', id=tenant.id))

    @app.route('/tenants/delete/<int:id>', methods=['POST'])
    @login_required
    def tenants_delete(id):
        tenant = Tenant.query.get_or_404(id)
        room_id = tenant.room_id

        # Safely disassociate maintenance tickets
        for req in tenant.maintenance_requests:
            req.tenant_id = None

        db.session.delete(tenant)
        db.session.commit()

        if room_id:
            room = db.session.get(Room, room_id)
            if room:
                room.update_occupancy_status()
                db.session.commit()

        flash('Tenant record and history were removed.', 'success')
        return redirect(url_for('tenants'))

    # -------------------------------------------------------------
    # Rent Payment Tracking Routes
    # -------------------------------------------------------------
    @app.route('/payments')
    @login_required
    def payments():
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()

        query = Payment.query.join(Tenant)
        if search:
            query = query.filter(
                (Tenant.full_name.ilike(f'%{search}%')) |
                (Payment.reference_number.ilike(f'%{search}%'))
            )
        if status_filter:
            query = query.filter(Payment.status == status_filter)

        payments_list = query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()

        # Financial summaries
        total_collected = sum(p.amount_paid for p in Payment.query.filter_by(status='Paid').all())
        unpaid_records = Payment.query.filter(Payment.status.in_(['Overdue', 'Partial'])).all()
        total_unpaid = sum(p.amount_paid for p in unpaid_records)
        overdue_count = len(unpaid_records)

        return render_template(
            'payments/index.html',
            active_page='payments',
            payments=payments_list,
            total_collected=total_collected,
            total_unpaid=total_unpaid,
            overdue_count=overdue_count,
            search=search,
            status_filter=status_filter
        )

    @app.route('/payments/add', methods=['GET', 'POST'])
    @login_required
    def payments_add():
        tenants = Tenant.query.filter_by(status='Active').order_by(Tenant.full_name.asc()).all()
        selected_tenant_id = request.args.get('tenant_id', '')
        default_amount = ''

        if selected_tenant_id and selected_tenant_id.isdigit():
            t = db.session.get(Tenant, int(selected_tenant_id))
            if t and t.room:
                default_amount = f"{t.room.monthly_rent:.2f}"

        if request.method == 'POST':
            tenant_id_raw = request.form.get('tenant_id', '')
            amount_raw = request.form.get('amount_paid', '0')
            payment_date_str = request.form.get('payment_date', '')
            due_date_str = request.form.get('due_date', '')
            payment_method = request.form.get('payment_method', 'Cash')
            status = request.form.get('status', 'Paid')
            reference_number = request.form.get('reference_number', '').strip() or None
            notes = request.form.get('notes', '').strip() or None

            if not tenant_id_raw or not tenant_id_raw.isdigit():
                flash('Please select a valid tenant.', 'error')
                return render_template('payments/form.html', active_page='payments', tenants=tenants, today=manila_today().isoformat())

            try:
                amount_paid = float(amount_raw)
                if amount_paid <= 0:
                    raise ValueError("Amount paid must be greater than zero.")
            except ValueError as e:
                flash(f'Invalid payment amount: {str(e)}', 'error')
                return render_template('payments/form.html', active_page='payments', tenants=tenants, today=manila_today().isoformat())

            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else manila_today()
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else manila_today()
            except ValueError:
                payment_date = manila_today()
                due_date = manila_today()

            new_payment = Payment(
                tenant_id=int(tenant_id_raw),
                amount_paid=amount_paid,
                payment_date=payment_date,
                due_date=due_date,
                payment_method=payment_method,
                status=status,
                reference_number=reference_number,
                notes=notes
            )
            db.session.add(new_payment)
            db.session.commit()

            flash(f'Payment of ₱{amount_paid:,.2f} recorded successfully!', 'success')
            return redirect(url_for('payments_receipt', id=new_payment.id))

        return render_template(
            'payments/form.html',
            active_page='payments',
            tenants=tenants,
            selected_tenant_id=selected_tenant_id,
            default_amount=default_amount,
            today=manila_today().isoformat()
        )

    @app.route('/payments/receipt/<int:id>')
    @login_required
    def payments_receipt(id):
        payment = Payment.query.get_or_404(id)
        return render_template('payments/receipt.html', active_page='payments', payment=payment)

    @app.route('/payments/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def payments_edit(id):
        payment = Payment.query.get_or_404(id)
        tenants = Tenant.query.order_by(Tenant.full_name.asc()).all()

        if request.method == 'POST':
            tenant_id_raw = request.form.get('tenant_id', '')
            amount_raw = request.form.get('amount_paid', '0')
            payment_date_str = request.form.get('payment_date', '')
            due_date_str = request.form.get('due_date', '')
            payment_method = request.form.get('payment_method', payment.payment_method)
            status = request.form.get('status', payment.status)
            reference_number = request.form.get('reference_number', '').strip() or None
            notes = request.form.get('notes', '').strip() or None

            if not tenant_id_raw or not tenant_id_raw.isdigit():
                flash('Please select a valid tenant.', 'error')
                return render_template('payments/form.html', active_page='payments', payment=payment, tenants=tenants, today=manila_today().isoformat())

            try:
                amount_paid = float(amount_raw)
                if amount_paid <= 0:
                    raise ValueError("Amount paid must be greater than zero.")
            except ValueError as e:
                flash(f'Invalid payment amount: {str(e)}', 'error')
                return render_template('payments/form.html', active_page='payments', payment=payment, tenants=tenants, today=manila_today().isoformat())

            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else payment.payment_date
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else payment.due_date
            except ValueError:
                payment_date = payment.payment_date
                due_date = payment.due_date

            payment.tenant_id = int(tenant_id_raw)
            payment.amount_paid = amount_paid
            payment.payment_date = payment_date
            payment.due_date = due_date
            payment.payment_method = payment_method
            payment.status = status
            payment.reference_number = reference_number
            payment.notes = notes

            db.session.commit()
            flash(f'Payment record #RCP-{payment.id:04d} updated successfully!', 'success')
            return redirect(url_for('payments'))

        return render_template(
            'payments/form.html',
            active_page='payments',
            payment=payment,
            tenants=tenants,
            today=manila_today().isoformat()
        )

    @app.route('/payments/delete/<int:id>', methods=['POST'])
    @login_required
    def payments_delete(id):
        payment = Payment.query.get_or_404(id)
        db.session.delete(payment)
        db.session.commit()
        flash('Payment record deleted.', 'info')
        return redirect(url_for('payments'))

    # -------------------------------------------------------------
    # Maintenance Request Routes
    # -------------------------------------------------------------
    @app.route('/maintenance')
    @login_required
    def maintenance():
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()

        query = MaintenanceRequest.query
        if search:
            query = query.filter(
                (MaintenanceRequest.title.ilike(f'%{search}%')) |
                (MaintenanceRequest.description.ilike(f'%{search}%'))
            )
        if status_filter:
            query = query.filter_by(status=status_filter)

        requests_list = query.order_by(MaintenanceRequest.created_at.desc()).all()
        return render_template(
            'maintenance/index.html',
            active_page='maintenance',
            requests=requests_list,
            search=search,
            status_filter=status_filter
        )

    @app.route('/maintenance/add', methods=['GET', 'POST'])
    @login_required
    def maintenance_add():
        rooms = Room.query.order_by(Room.room_number.asc()).all()
        tenants = Tenant.query.filter_by(status='Active').order_by(Tenant.full_name.asc()).all()

        if request.method == 'POST':
            room_id_raw = request.form.get('room_id', '')
            tenant_id_raw = request.form.get('tenant_id', '')
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            priority = request.form.get('priority', 'Medium')
            cost_raw = request.form.get('cost', '0')

            if not room_id_raw or not room_id_raw.isdigit():
                flash('Please select a valid room.', 'error')
                return render_template('maintenance/form.html', active_page='maintenance', rooms=rooms, tenants=tenants)

            if not title or not description:
                flash('Title and detailed description are required.', 'error')
                return render_template('maintenance/form.html', active_page='maintenance', rooms=rooms, tenants=tenants)

            try:
                cost = float(cost_raw) if cost_raw else 0.0
            except ValueError:
                cost = 0.0

            tenant_id = int(tenant_id_raw) if tenant_id_raw and tenant_id_raw.isdigit() else None

            new_req = MaintenanceRequest(
                room_id=int(room_id_raw),
                tenant_id=tenant_id,
                title=title,
                description=description,
                priority=priority,
                status='Pending',
                cost=cost,
                reported_date=manila_today()
            )
            db.session.add(new_req)
            db.session.commit()

            flash('Maintenance request submitted successfully.', 'success')
            return redirect(url_for('maintenance'))

        return render_template('maintenance/form.html', active_page='maintenance', rooms=rooms, tenants=tenants)

    @app.route('/maintenance/status/<int:id>', methods=['POST'])
    @login_required
    def maintenance_update_status(id):
        req = MaintenanceRequest.query.get_or_404(id)
        new_status = request.form.get('status', req.status)

        if new_status in ('Pending', 'In Progress', 'Resolved'):
            req.status = new_status
            if new_status == 'Resolved':
                req.resolved_date = manila_today()
            else:
                req.resolved_date = None
            db.session.commit()
            flash(f'Maintenance ticket updated to "{new_status}".', 'success')

        return redirect(url_for('maintenance'))

    @app.route('/maintenance/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def maintenance_edit(id):
        req = MaintenanceRequest.query.get_or_404(id)
        rooms = Room.query.order_by(Room.room_number.asc()).all()
        tenants = Tenant.query.order_by(Tenant.full_name.asc()).all()

        if request.method == 'POST':
            room_id_raw = request.form.get('room_id', '')
            tenant_id_raw = request.form.get('tenant_id', '')
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            priority = request.form.get('priority', req.priority)
            status = request.form.get('status', req.status)
            cost_raw = request.form.get('cost', '0')

            if not room_id_raw or not room_id_raw.isdigit():
                flash('Please select a valid room.', 'error')
                return render_template('maintenance/form.html', active_page='maintenance', req=req, rooms=rooms, tenants=tenants)

            if not title or not description:
                flash('Title and detailed description are required.', 'error')
                return render_template('maintenance/form.html', active_page='maintenance', req=req, rooms=rooms, tenants=tenants)

            try:
                cost = float(cost_raw) if cost_raw else 0.0
            except ValueError:
                cost = 0.0

            req.room_id = int(room_id_raw)
            req.tenant_id = int(tenant_id_raw) if tenant_id_raw and tenant_id_raw.isdigit() else None
            req.title = title
            req.description = description
            req.priority = priority
            req.cost = cost
            if status != req.status:
                req.status = status
                if status == 'Resolved':
                    req.resolved_date = manila_today()
                else:
                    req.resolved_date = None

            db.session.commit()
            flash(f'Maintenance ticket #{req.id} updated successfully.', 'success')
            return redirect(url_for('maintenance'))

        return render_template('maintenance/form.html', active_page='maintenance', req=req, rooms=rooms, tenants=tenants)

    @app.route('/maintenance/delete/<int:id>', methods=['POST'])
    @login_required
    def maintenance_delete(id):
        req = MaintenanceRequest.query.get_or_404(id)
        db.session.delete(req)
        db.session.commit()
        flash('Maintenance ticket deleted.', 'info')
        return redirect(url_for('maintenance'))

    # -------------------------------------------------------------
    # Reports Route
    # -------------------------------------------------------------
    @app.route('/reports')
    @login_required
    def reports():
        all_rooms = Room.query.order_by(Room.room_number.asc()).all()
        all_tenants = Tenant.query.order_by(Tenant.full_name.asc()).all()
        all_payments = Payment.query.order_by(Payment.payment_date.desc()).all()

        total_rooms = len(all_rooms)
        total_capacity = sum(r.capacity for r in all_rooms)
        total_active_tenants = sum(1 for t in all_tenants if t.status == 'Active')
        total_occupied_slots = sum(r.active_tenants_count for r in all_rooms)
        available_slots = max(0, total_capacity - total_occupied_slots)
        maintenance_rooms = sum(1 for r in all_rooms if r.status == 'Maintenance')
        occupancy_rate = round((total_occupied_slots / total_capacity * 100), 1) if total_capacity > 0 else 0

        paid_payments = [p for p in all_payments if p.status == 'Paid']
        overdue_payments = [p for p in all_payments if p.status in ('Overdue', 'Partial')]
        total_collected = sum(p.amount_paid for p in paid_payments)
        total_unpaid = sum(p.amount_paid for p in overdue_payments)

        cash_total = sum(p.amount_paid for p in paid_payments if p.payment_method == 'Cash')
        online_total = sum(p.amount_paid for p in paid_payments if p.payment_method in ('GCash', 'Bank Transfer'))

        report_time = manila_now().strftime('%B %d, %Y at %I:%M %p')

        return render_template(
            'reports/index.html',
            active_page='reports',
            rooms=all_rooms,
            tenants=all_tenants,
            payments=all_payments,
            total_rooms=total_rooms,
            total_capacity=total_capacity,
            total_active_tenants=total_active_tenants,
            available_slots=available_slots,
            maintenance_rooms=maintenance_rooms,
            occupancy_rate=occupancy_rate,
            total_collected=total_collected,
            total_unpaid=total_unpaid,
            paid_count=len(paid_payments),
            overdue_count=len(overdue_payments),
            cash_total=cash_total,
            online_total=online_total,
            report_time=report_time
        )

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
