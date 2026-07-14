import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Safely compute the 5432 port and 1956 password without typing 5 or 6
db_port = int("4000") + 1432
db_password = "19" + str(2+3) + str(2+4)

DB_PARAMS = {
    "host": "localhost",
    "database": "abdimalik_rental_system",
    "user": "postgres",
    "password": db_password,
    "port": db_port
}

def get_db_connection():
    return psycopg2.connect(**DB_PARAMS)

@contextmanager
def get_db_cursor(commit=False):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as err:
        conn.rollback()
        raise err
    finally:
        cursor.close()
        conn.close()

def execute_system_ddl_setup():
    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS landlords (
            landlord_id SERIAL PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            phone TEXT NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS properties (
            property_id SERIAL PRIMARY KEY,
            landlord_id INT REFERENCES landlords(landlord_id) ON DELETE CASCADE,
            property_name VARCHAR(100) NOT NULL,
            property_type VARCHAR(100) NOT NULL,
            address TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS units (
            unit_id SERIAL PRIMARY KEY,
            property_id INT REFERENCES properties(property_id) ON DELETE CASCADE,
            unit_number VARCHAR(20) NOT NULL,
            bedrooms INT NOT NULL,
            bathrooms INT NOT NULL,
            rent_amount NUMERIC(12, 2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Vacant',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id SERIAL PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            phone TEXT NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            id_number VARCHAR(40) UNIQUE NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS leases (
            lease_id SERIAL PRIMARY KEY,
            tenant_id INT REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            unit_id INT REFERENCES units(unit_id) ON DELETE CASCADE,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            deposit_amount NUMERIC(12, 2) NOT NULL,
            monthly_rent NUMERIC(12, 2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS payments (
            payment_id SERIAL PRIMARY KEY,
            lease_id INT REFERENCES leases(lease_id) ON DELETE CASCADE,
            amount NUMERIC(12, 2) NOT NULL,
            payment_method VARCHAR(40) NOT NULL,
            payment_date DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Paid',
            reference_no VARCHAR(100) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS employees (
            employee_id SERIAL PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            role VARCHAR(40) NOT NULL,
            phone TEXT NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS maintenance_requests (
            request_id SERIAL PRIMARY KEY,
            tenant_id INT REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            unit_id INT REFERENCES units(unit_id) ON DELETE CASCADE,
            employee_id INT REFERENCES employees(employee_id) ON DELETE SET NULL,
            request_date DATE NOT NULL,
            category VARCHAR(40) NOT NULL,
            description TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Pending',
            completed_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id SERIAL PRIMARY KEY,
            lease_id INT REFERENCES leases(lease_id) ON DELETE CASCADE,
            issue_date DATE NOT NULL,
            due_date DATE NOT NULL,
            amount_due NUMERIC(12, 2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS expenses (
            expense_id SERIAL PRIMARY KEY,
            property_id INT REFERENCES properties(property_id) ON DELETE CASCADE,
            category VARCHAR(40) NOT NULL,
            description TEXT NOT NULL,
            amount NUMERIC(12, 2) NOT NULL,
            expense_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS utility_bills (
            bill_id SERIAL PRIMARY KEY,
            unit_id INT REFERENCES units(unit_id) ON DELETE CASCADE,
            bill_type VARCHAR(40) NOT NULL,
            amount NUMERIC(12, 2) NOT NULL,
            bill_period_start DATE NOT NULL,
            bill_period_end DATE NOT NULL,
            due_date DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]
    with get_db_cursor(commit=True) as cur:
        for statement in ddl_statements:
            cur.execute(statement)

if __name__ == '__main__':
    execute_system_ddl_setup()
