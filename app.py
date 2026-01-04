from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)   # Create flask application
app.secret_key = "your_secret_key_here"   # Secret key to encrypt session data

# Get DATABASE_URL from Render environment
DATABASE_URL = os.environ.get("DATABASE_URL")

# Database connection
def get_db():
    return psycopg2.connect(DATABASE_URL)

# Initialise database
def init_db():
    conn = get_db()     # Creates tables if they do not exist
    cursor = conn.cursor()
 
    cursor.execute("""      
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)    # Users table for authentication
 
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices(
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        customer_name TEXT,
        customer_address TEXT,
        date TEXT,
        invoice_no TEXT,
        description TEXT,
        invoice_total REAL,
        status TEXT DEFAULT 'Unpaid'
    )
    """)    # Invoices table linked to users
 
    conn.commit()
    conn.close()

init_db()   # Run database setup when the app starts

# Helper functions
def get_invoices():
    if "user_id" not in session:
        return []

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM invoices WHERE user_id=%s",
        (session["user_id"],)   # Select invoices for logged-in user only
    )
    invoices = cursor.fetchall()
    conn.close()
    return invoices

# Authentication routes
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:    # Validate input
            return render_template("signup.html", error="All fields required")

        if len(password) < 8:
            return render_template("signup.html", error="Password must be at least 8 characters")

        try:
            conn = get_db()   # Insert new user into database
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id",
                (username, password)
            )
            user_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()

            session["user_id"] = user_id   # Log user in immediately
            session["username"] = username
            return redirect("/")

        except psycopg2.IntegrityError:   # Check for duplicate usernames
            return render_template("signup.html", error="Username already exists")

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)     # Fetch user by username
        )
        user = cursor.fetchone()
        conn.close()

        if not user or user[2] != password:   # Validate password
            return render_template("login.html", error="Invalid login details")

        session["user_id"] = user[0]    # Store user info in session
        session["username"] = user[1]
        return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():   # Clear session to logout user
    session.clear()
    return redirect("/login")

# Invoice routes
@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        return redirect("/login")

    error_invoice_total = None
    error_date = None

    if request.method == "POST":
        customer_name = request.form["customer_name"].strip()
        customer_address = request.form["customer_address"].strip()
        date = request.form["date"].strip()
        invoice_no = request.form["invoice_no"].strip()
        description = request.form["description"].strip()
        try:
            invoice_total = float(request.form["invoice_total"].strip())
        except ValueError:   # Invalid total format
            error_invoice_total = "Invalid invoice total format"
            invoice_total = None

        # Date validation (DD/MM/YYYY)
        try:
            datetime.datetime.strptime(date, "%d/%m/%Y")
        except ValueError:
            error_date = "Invalid date format. Use DD/MM/YYYY"

        if not error_invoice_total and not error_date:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO invoices (user_id, customer_name, customer_address, date, invoice_no, description, invoice_total) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (session["user_id"], customer_name, customer_address, date, invoice_no, description, invoice_total)
            )
            conn.commit()
            conn.close()
            return redirect("/")

    invoices = get_invoices()
    return render_template("index.html", invoices=invoices, error_invoice_total=error_invoice_total, error_date=error_date)

if __name__ == "__main__":
    app.run(debug=True)
