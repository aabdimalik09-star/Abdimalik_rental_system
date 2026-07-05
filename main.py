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
    # If a user is already logged in, take them straight to properties
    if 'user_id' in session:
        return redirect(url_for('manage_properties'))

    if request.method == 'POST':
        # Safely read what the user typed into the form fields
        email_input = request.form.get('username') or request.form.get('email')
        password_input = request.form.get('password')

        with get_db_cursor() as cur:
            # Query using exact columns from your users table schema
            cur.execute("SELECT user_id, email, password FROM users WHERE email = %s", (email_input,))
            user = cur.fetchone()

            # Using string keys ('password', 'user_id') to prevent KeyError 2
            if user and str(user['password']).strip() == str(password_input).strip():
                session['user_id'] = user['user_id']  
                flash('Portal authorization granted.')
                return redirect(url_for('manage_properties'))
            else:
                flash('Access Denied: Invalid Username or Password.')
                return redirect(url_for('login'))

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
        # Grab data from the HTML form fields
        name = request.form.get('property_name')
        location = request.form.get('location_district')
        category = request.form.get('property_category')
        # Using a dummy or default landlord_id (e.g., 1) if not selected yet to prevent NOT NULL errors
        landlord_id = request.form.get('landlord_id', 1) 

        with get_db_cursor(commit=True) as cur:
            # Matches your exact columns: landlord_id, property_name, property_type, address
            cur.execute("""
                INSERT INTO properties (landlord_id, property_name, property_type, address, description) 
                VALUES (%s, %s, %s, %s, %s)
            """, (int(landlord_id), name, category, location, ""))
            
        flash('Property asset registered successfully.')
        return redirect(url_for('manage_properties'))

    with get_db_cursor() as cur:
        # Fetching using the exact columns from your schema
        cur.execute("SELECT property_id, property_name, address, property_type FROM properties ORDER BY property_id DESC")
        properties_dataset = cur.fetchall()

        return render_template('properties.html', properties=properties_dataset)
           
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



@app.route('/maintenance', methods=['GET', 'POST'])
def manage_maintenance():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        unit_id = request.form.get('unit_id')
        description = request.form.get('description')
        urgency = request.form.get('urgency_level')

        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO maintenance_requests (unit_id, description, urgency, status) 
                VALUES (%s, %s, %s, %s)
            """, (int(unit_id), description, urgency, 'PENDING'))
            
        flash('Maintenance ticket safely registered in work cycle.')
        return redirect(url_for('manage_maintenance'))

    with get_db_cursor() as cur:
        # Corrected joins to use unit_id and property_id
        cur.execute("""
            SELECT m.*, u.unit_number, p.property_name 
            FROM maintenance_requests m
            JOIN units u ON m.unit_id = u.unit_id
            JOIN properties p ON u.property_id = p.property_id
        """)
        tickets = cur.fetchall()

        cur.execute("""
            SELECT u.unit_id, u.unit_number, p.property_name 
            FROM units u
            JOIN properties p ON u.property_id = p.property_id
        """)
        available_units = cur.fetchall()

        return render_template('maintenance.html', tickets=tickets, units=available_units)
    

@app.route('/invoices', methods=['GET', 'POST'])
def manage_invoices():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        lease_id = request.form.get('lease_id')
        issue_date = request.form.get('issue_date')
        due_date = request.form.get('due_date')
        amount_due = request.form.get('amount_due')
        status = request.form.get('status')

        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO invoices (lease_id, issue_date, due_date, amount_due, status) 
                VALUES (%s, %s, %s, %s, %s)
            """, (int(lease_id), issue_date, due_date, float(amount_due), status))
            
        flash('Invoice successfully generated.')
        return redirect(url_for('manage_invoices'))

    with get_db_cursor() as cur:
        # Fetching invoices to display in the table
        cur.execute("SELECT invoice_id, lease_id, issue_date, due_date, amount_due, status FROM invoices ORDER BY invoice_id DESC")
        invoice_dataset = cur.fetchall()

        # Optional: Fetch active leases to populate a dropdown selector in your form
        cur.execute("SELECT lease_id FROM leases")
        active_leases = cur.fetchall()

        return render_template('invoices.html', invoices=invoice_dataset, leases=active_leases)

    

@app.route('/employees', methods=['GET', 'POST'])
def manage_employees():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        full_name = request.form.get('employee_name')
        role = request.form.get('operational_role')
        email = request.form.get('employee_email')
        phone = request.form.get('contact_phone')

        with get_db_cursor(commit=True) as cur:
            # Matches your exact database columns from 71716.jpg
            cur.execute("""
                INSERT INTO employees (full_name, role, email, phone) 
                VALUES (%s, %s, %s, %s)
            """, (full_name, role, email, phone))
            
        flash('Employee profile registered in administration roster.')
        return redirect(url_for('manage_employees'))

    with get_db_cursor() as cur:
        # Fixed query to only select columns that actually exist
        cur.execute("SELECT employee_id, full_name, role, email, phone FROM employees")
        workforce_dataset = cur.fetchall()

        return render_template('employees.html', employees=workforce_dataset)







if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)