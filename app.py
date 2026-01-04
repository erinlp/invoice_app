# Import the rquired libraries
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
import datetime
 
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
def signup():   # Handles form submission
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
            hashed_password = generate_password_hash(password)

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id",
                (username, hashed_password)
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
 
        if not user or not check_password_hash(user[2], password):   # Validate password
            return render_template("login.html", error="Invalid login details")
 
        session["user_id"] = user[0]    # Store user info in session
        session["username"] = user[1]
        return redirect("/")
 
    return render_template("login.html")
 
@app.route("/logout")
def logout():   # Clear session data 
    session.clear()
    return redirect("/login")
 
# Invoice routes
@app.route("/", methods=["GET", "POST"])
def home():   
    if "user_id" not in session:    # Require login
        return redirect("/login")

    invoices = get_invoices()   # Show all invoices
 
    if request.method == "POST":    # Handle new invoice submission
        customer_name = request.form["customer_name"].strip()
        customer_address = request.form["customer_address"].strip()
        date = request.form["date"].strip()
        invoice_no = request.form["invoice_no"].strip()
        description = request.form["description"].strip()
        invoice_total = request.form["invoice_total"].strip()
 
        if not all([customer_name, customer_address, date, invoice_no, description, invoice_total]):    # Check that all fields are filled
            return render_template(
                "index.html",
                invoices=invoices,
                error="All fields are required"
            )
 
        try:
            invoice_total = float(invoice_total)    # Validate number and date formats
            datetime.datetime.strptime(date, "%d/%m/%Y")
        except ValueError:
            return render_template(
                "index.html",
                invoices=invoices,
                error="Invalid date or invoice total format (DD/MM/YYYY)"
            )
 
        conn = get_db()    # Insert new invoice into database
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO invoices
        (user_id, customer_name, customer_address, date, invoice_no, description, invoice_total)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session["user_id"],
            customer_name,
            customer_address,
            date,
            invoice_no,
            description,
            invoice_total
        ))
        conn.commit()
        conn.close()
 
        return redirect("/")
 
    return render_template("index.html", invoices=invoices)
 
@app.route("/delete/<int:id>")
def delete(id):
    if "user_id" not in session:    # Require login
        return redirect("/login")
 
    conn = get_db()
    cursor = conn.cursor()  # Delete invoice for logged-in user only
    cursor.execute(
        "DELETE FROM invoices WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )
    conn.commit()
    conn.close()
 
    return redirect("/")
 
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user_id" not in session:    # Require login
        return redirect("/login")
 
    conn = get_db()
    cursor = conn.cursor()
 
    cursor.execute(
        "SELECT * FROM invoices WHERE id=%s AND user_id=%s",
        (id, session["user_id"])    # Fetch invoice to edit
    )
    invoice = cursor.fetchone()
 
    if request.method == "POST":    # Handle invoice submission 
        customer_name = request.form["customer_name"]
        customer_address = request.form["customer_address"]
        date = request.form["date"]
        invoice_no = request.form["invoice_no"]
        description = request.form["description"]
        invoice_total = float(request.form["invoice_total"])
        status = request.form.get("status", "Unpaid")
 
        cursor.execute("""
        UPDATE invoices
        SET customer_name=%s, customer_address=%s, date=%s,
            invoice_no=%s, description=%s, invoice_total=%s, status=%s
        WHERE id=%s AND user_id=%s
        """, (
            customer_name,
            customer_address,
            date,
            invoice_no,
            description,
            invoice_total,
            status,
            id,
            session["user_id"]
        ))  # Update invoice 
 
        conn.commit()
        conn.close()
        return redirect("/")
 
    conn.close()
    return render_template("edit.html", invoice=invoice)
 
# Run app 
if __name__ == "__main__":
    app.run(debug=True)
