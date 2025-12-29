from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
import datetime
 
app = Flask(__name__)
app.secret_key = "your_secret_key_here"
 
# Get DATABASE_URL from Render environment
DATABASE_URL = os.environ.get("DATABASE_URL")
 
# --------------------
# Database connection
# --------------------
def get_db():
    return psycopg2.connect(DATABASE_URL)
 
# --------------------
# Initialise database
# --------------------
def init_db():
    conn = get_db()
    cursor = conn.cursor()
 
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)
 
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
    """)
 
    conn.commit()
    conn.close()
 
init_db()
 
# --------------------
# Helper functions
# --------------------
def get_invoices():
    if "user_id" not in session:
        return []
 
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM invoices WHERE user_id=%s",
        (session["user_id"],)
    )
    invoices = cursor.fetchall()
    conn.close()
    return invoices
 
# --------------------
# Auth routes
# --------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
 
        if not username or not password:
            return render_template("signup.html", error="All fields required")
 
        if len(password) < 8:
            return render_template("signup.html", error="Password must be at least 8 characters")
 
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            conn.commit()
            conn.close()
            return redirect("/login")
        except psycopg2.IntegrityError:
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
            (username,)
        )
        user = cursor.fetchone()
        conn.close()
 
        if not user or user[2] != password:
            return render_template("login.html", error="Invalid login details")
 
        session["user_id"] = user[0]
        session["username"] = user[1]
        return redirect("/")
 
    return render_template("login.html")
 
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
 
# --------------------
# Invoice routes
# --------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect("/login")
 
    if request.method == "POST":
        customer_name = request.form["customer_name"].strip()
        customer_address = request.form["customer_address"].strip()
        date = request.form["date"].strip()
        invoice_no = request.form["invoice_no"].strip()
        description = request.form["description"].strip()
        invoice_total = request.form["invoice_total"].strip()
 
        if not all([customer_name, customer_address, date, invoice_no, description, invoice_total]):
            return "All fields required"
 
        try:
            invoice_total = float(invoice_total)
            datetime.datetime.strptime(date, "%d/%m/%Y")
        except ValueError:
            return "Invalid data format"
 
        conn = get_db()
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
 
    invoices = get_invoices()
    return render_template("index.html", invoices=invoices)
 
@app.route("/delete/<int:id>")
def delete(id):
    if "user_id" not in session:
        return redirect("/login")
 
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM invoices WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )
    conn.commit()
    conn.close()
 
    return redirect("/")
 
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user_id" not in session:
        return redirect("/login")
 
    conn = get_db()
    cursor = conn.cursor()
 
    cursor.execute(
        "SELECT * FROM invoices WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )
    invoice = cursor.fetchone()
 
    if request.method == "POST":
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
        ))
 
        conn.commit()
        conn.close()
        return redirect("/")
 
    conn.close()
    return render_template("edit.html", invoice=invoice)
 
# --------------------
# Run app (local only)
# --------------------
if __name__ == "__main__":
    app.run(debug=True)