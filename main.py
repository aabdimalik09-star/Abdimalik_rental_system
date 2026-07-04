from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import get_db_cursor, execute_system_ddl_setup

app = Flask(__name__)
app.secret_key = 'abdimalik_rental_system_core_key'

# Instantly construct or verify tables on spin-up
execute_system_ddl_setup()


@app.route('/')
def index():
    return render_template('index.html')


# --- AUTHENTICATION LAYER ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_email = request.form.get('email')
        user_pwd = request.form.get('password')
        
        query = "SELECT user_id, full_name, password FROM users WHERE email = %s;"
        with get_db_cursor() as cur:
            cur.execute(query, (user_email,))
            account = cur.fetchone()
            
        if account and account['password'] == user_pwd:
            session['user_id'] = account['user_id']
            session['user_name'] = account['full_name']
            flash('Login confirmed.')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid user credentials.')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('login'))


# --- FULLY REALIZED DASHBOARD ROUTE SIGNATURES ---
@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    metrics = {}
    with get_db_cursor() as cur:
        tables_to_check = ['landlords', 'properties', 'units', 'tenants', 'employees', 'expenses']
        for table in tables_to_check:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            metrics[table] = cur.fetchone()['count']
            
        cur.execute("SELECT COUNT(*) FROM leases WHERE status = 'Active';")
        metrics['active_leases'] = cur.fetchone()['count']
        
        # Pull live payment streams to populate dashboard table
        cur.execute("""
            SELECT p.payment_id, p.amount, p.payment_method, p.payment_date, p.reference_no, t.full_name
            FROM payments p
            JOIN leases l ON p.lease_id = l.lease_id
            JOIN tenants t ON l.tenant_id = t.tenant_id
            ORDER BY p.payment_date DESC LIMIT 8;
        """)
        recent_payments = cur.fetchall()
        
    return render_template('dashboard.html', data=metrics, payments=recent_payments)


# --- 1. LANDLORDS ---
@app.route('/landlords', methods=['GET', 'POST'])
def manage_landlords():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        name = request.form.get('full_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        addr = request.form.get('address')
        
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO landlords (full_name, phone, email, address) VALUES (%s, %s, %s, %s);",
                (name, phone, email, addr)
            )
        flash('Landlord catalog updated.')
        return redirect(url_for('manage_landlords'))
        
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM landlords ORDER BY landlord_id DESC;")
        dataset = cur.fetchall()
    return render_template('landlords.html', landlords=dataset)


# --- 2. PROPERTIES ---
@app.route('/properties', methods=['GET', 'POST'])
def manage_properties():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        name = request.form.get('property_name')
        p_type = request.form.get('property_type')
        addr = request.form.get('address')
        desc = request.form.get('description')
        landlord = request.form.get('landlord_id')
        
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO properties (property_name, property_type, address, description, landlord_id) VALUES (%s, %s, %s, %s, %s);",
                (name, p_type, addr, desc, int(landlord))
            )
        flash('Property assets saved.')
        return redirect(url_for('manage_properties'))
        
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT p.*, l.full_name as landlord_name 
            FROM properties p 
            JOIN landlords l ON p.landlord_id = l.landlord_id ORDER BY p.property_id DESC;
        """)
        dataset = cur.fetchall()
        cur.execute("SELECT landlord_id, full_name FROM landlords;")
        landlords_dropdown = cur.fetchall()
    return render_template('properties.html', properties=dataset, landlords=landlords_dropdown)


# --- 3. UNITS ---
@app.route('/units', methods=['GET', 'POST'])
def manage_units():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        prop_id = request.form.get('property_id')
        number = request.form.get('unit_number')
        beds = request.form.get('bedrooms')
        baths = request.form.get('bathrooms')
        rent = request.form.get('rent_amount')
        stat = request.form.get('status')
        
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO units (property_id, unit_number, bedrooms, bathrooms, rent_amount, status) VALUES (%s, %s, %s, %s, %s, %s);",
                (int(prop_id), number, int(beds), int(baths), float(rent), stat)
            )
        flash('Unit recorded.')
        return redirect(url_for('manage_units'))
        
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT u.*, p.property_name FROM units u 
            JOIN properties p ON u.property_id = p.property_id ORDER BY u.unit_id DESC;
        """)
        dataset = cur.fetchall()
        cur.execute("SELECT property_id, property_name FROM properties;")
        properties_dropdown = cur.fetchall()
    return render_template('units.html', units=dataset, properties=properties_dropdown)


# --- 4. TENANTS ---
@app.route('/tenants', methods=['GET', 'POST'])
def manage_tenants():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        name = request.form.get('full_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        id_card = request.form.get('id_number')
        addr = request.form.get('address')
        
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO tenants (full_name, phone, email, id_number, address) VALUES (%s, %s, %s, %s, %s);",
                (name, phone, email, id_card, addr)
            )
        flash('Tenant recorded.')
        return redirect(url_for('manage_tenants'))
        
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM tenants ORDER BY tenant_id DESC;")
        dataset = cur.fetchall()
    return render_template('tenants.html', tenants=dataset)


# --- 5. LEASES ---
@app.route('/leases', methods=['GET', 'POST'])
def manage_leases():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        tenant = request.form.get('tenant_id')
        unit = request.form.get('unit_id')
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        deposit = request.form.get('deposit_amount')
        rent = request.form.get('monthly_rent')
        stat = request.form.get('status')
        
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO leases (tenant_id, unit_id, start_date, end_date, deposit_amount, monthly_rent, status) VALUES (%s, %s, %s, %s, %s, %s, %s);",
                (int(tenant), int(unit), start, end, float(deposit), float(rent), stat)
            )
        flash('Lease recorded.')
        return redirect(url_for('manage_leases'))
        
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT l.*, t.full_name as tenant_name, u.unit_number FROM leases l
            JOIN tenants t ON l.tenant_id = t.tenant_id
            JOIN units u ON l.unit_id = u.unit_id ORDER BY l.lease_id DESC;
        """)
        dataset = cur.fetchall()
        cur.execute("SELECT tenant_id, full_name FROM tenants;")
        tenants_dropdown = cur.fetchall()
        cur.execute("SELECT unit_id, unit_number FROM units WHERE status != 'Occupied';")
        units_dropdown = cur.fetchall()
    return render_template('leases.html', leases=dataset, tenants=tenants_dropdown, units=units_dropdown)


# --- 6. PAYMENTS ---
@app.route('/payments', methods=['GET', 'POST'])
def manage_payments():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        lease = request.form.get('lease_id')
        amt = request.form.get('amount')
        method = request.form.get('payment_method')
        p_date = request.form.get('payment_date')
        stat = request.form.get('status')
        ref = request.form.get('reference_no')
        
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO payments (lease_id, amount, payment_method, payment_date, status, reference_no) VALUES (%s, %s, %s, %s, %s, %s);",
                (int(lease), float(amt), method, p_date, stat, ref)
            )
        flash('Payment transaction finalized.')
        return redirect(url_for('manage_payments'))
        
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT p.*, t.full_name FROM payments p
            JOIN leases l ON p.lease_id = l.lease_id
            JOIN tenants t ON l.tenant_id = t.tenant_id ORDER BY p.payment_id DESC;
        """)
        dataset = cur.fetchall()
        cur.execute("""
            SELECT l.lease_id, t.full_name, u.unit_number FROM leases l
            JOIN tenants t ON l.tenant_id = t.tenant_id
            JOIN units u ON l.unit_id = u.unit_id WHERE l.status = 'Active';
        """)
        leases_dropdown = cur.fetchall()
    return render_template('payments.html', payments=dataset, leases=leases_dropdown)


# --- REGISTRATION ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('full_name')
        email = request.form.get('email')
        pwd = request.form.get('password')
        
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s);",
                (name, email, pwd)
            )
        flash("Account created successfully.")
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/invoices', methods=['GET', 'POST'])
def manage_invoices():
    # Your logic here
    return render_template('invoices.html')

@app.route('/maintenance', methods=['GET', 'POST'])
def manage_maintenance():
    # Your logic here
    return render_template('maintenance.html')

@app.route('/employees', methods=['GET', 'POST'])
def manage_employees():
    # Your logic here
    return render_template('employees.html')







if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)