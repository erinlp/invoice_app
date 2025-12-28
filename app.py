from flask import Flask, render_template, request, redirect, session
import sqlite3
import datetime
 
app = Flask(__name__)   # Create the flask app

app.secret_key = "your_secret_key_here"  # Secret key for session management, nessacery for flask to handle sessions
 
# Database functions 

def get_db():
    return sqlite3.connect("database.db")   # Function to get a connection to the database

def init_db():  
    conn = get_db()     # Connect to database
    cursor = conn.cursor()

    # Create the users table

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # Create the invoices table

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        customer_name TEXT,
        customer_address TEXT,
        date TEXT,
        invoice_no TEXT,
        description TEXT,
        invoice_total REAL,
        status TEXT DEFAULT 'Unpaid',
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()   #Commit changes and close the connection to the database 
    conn.close()
 
init_db()   #Call from this function when the app starts to make sure the tables are set up
 
def get_invoices():     # Fetch the invoices for the logged in user 

    if "user_id" not in session:    # If the user isnt logged in return an empty list
        return []

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE user_id=?", (session["user_id"],))
    rows = cursor.fetchall()
    conn.close()

    return rows     # Return the invoices for the user
 
# User routes

@app.route("/signup", methods=["GET", "POST"])     # Route for signing up a new user

def signup():

    if request.method == "POST":
        username = request.form["username"].strip()     # Get the username and password from the form
        password = request.form["password"].strip()

        if not username or not password:
            return render_template("signup.html", error="Username and password cannot be empty")    # Check to see if any fields are empty

        if len(password) < 8:
            return render_template("signup.html", error="Password must be at least 8 characters")   # Check to see if the password is long enough 

        try:
            conn = get_db()     # Add the new user to the database
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect("/login")   # Redirect the user to the login page

        except sqlite3.IntegrityError:

            return render_template("signup.html", error="Username already exists")      # If the user already exisists show an error message

    return render_template("signup.html")   # Show the signup form if its a GET request
 
@app.route("/login", methods=["GET", "POST"])   # Route for logging in

def login():

    if request.method == "POST":
        username = request.form["username"].strip()     # Get the username and password from the form
        password = request.form["password"].strip()

        if not username or not password:
            return render_template("login.html", error="Please enter both username and password")   # Make sure all the fields are filled out 

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))

        user = cursor.fetchone()

        conn.close()

        if not user:
            return render_template("login.html", error="Username does not exist")   # Check that the username exists and password is correct 

        elif user[2] != password:
            return render_template("login.html", error="Incorrect password")

        else:
            session["user_id"] = user[0]    # Store the users ID in the session
            session["username"] = user[1]   # Store the username in the session
            return redirect("/")    # Redirect to the home page after logging in

    return render_template("login.html")    # If its a GET request show the log in form
 
@app.route("/logout")   # Rotue to log user out

def logout():
    session.clear()     # Clears the session
    return redirect("/login")   # Redirects to login page after logging out
 
# Invoice routes

@app.route("/", methods=["GET", "POST"])    # Home page where users can add and view invoices

def home():
    if "user_id" not in session:    # If the user isnt lgged in redirect to login page
        return redirect("/login")
 
    if request.method == "POST":    # Handles invoice creation when the form is subbmitted
        customer_name = request.form["customer_name"].strip()   # Get the invoice details from the form
        customer_address = request.form["customer_address"].strip()
        date = request.form["date"].strip()
        invoice_no = request.form["invoice_no"].strip()
        description = request.form["description"].strip()
        invoice_total = request.form["invoice_total"].strip()
 
        if not all([customer_name, customer_address, date, invoice_no, description, invoice_total]):    # Check that all of the fields have been filled out
            return "All fields are required"
 
        try:
            invoice_total = float(invoice_total)    # Convert total invoice total to a float

        except ValueError:
            return "Invoice total must be a number"
 
        try:
            datetime.datetime.strptime(date, "%d/%m/%Y")    # Make sure that the date is in the right format

        except ValueError:
            return "Date must be in DD/MM/YYYY format"
 
        conn = get_db()     # Add the invoice into the database
    
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO invoices (user_id, customer_name, customer_address, date, invoice_no, description, invoice_total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
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
        return redirect("/")    # Redirect back to the home page after adding an invoice
 
    invoices = get_invoices()   # Get all of the invoices for the logged in user
    return render_template("index.html", invoices=invoices)     # Show the user the invices on the homepage
 
@app.route("/delete/<int:id>")      # Route to delete an invoice

def delete(id):
    if "user_id" not in session:    # Check if the user is logged in before letting them delete an invoice
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM invoices WHERE id=? AND user_id=?", (id, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/")    # After deleting redirect to the home page
 
@app.route("/edit/<int:id>", methods=["GET", "POST"])   # Route to edit an invoice

def edit(id):
    if "user_id" not in session:    # Make sure the user is logged in before letting them edit an invoice
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE id=? AND user_id=?", (id, session["user_id"]))
    invoice = cursor.fetchone()
 
    if request.method == "POST":    # If its a POST request, update the invoice details 
        customer_name = request.form["customer_name"].strip()   # Get the updated invoice details from the form
        customer_address = request.form["customer_address"].strip()
        date = request.form["date"].strip()
        invoice_no = request.form["invoice_no"].strip()
        description = request.form["description"].strip()
        invoice_total = request.form["invoice_total"].strip()
        status = request.form.get("status", "Unpaid")   # Default is 'unpaid' if no status has been provided
 
        if not all([customer_name, customer_address, date, invoice_no, description, invoice_total]):     # Make sure all the fields are filled and not empty
            return "All fields are required"
 
        try:
            invoice_total = float(invoice_total)    # Convert invoice total to a float

        except ValueError:
            return "Invoice total must be a number"
 
        if status not in ["Paid", "Unpaid"]:    # Make sure the status is either paid or unpaid
            return "Invalid status"
 
        try:
            datetime.datetime.strptime(date, "%d/%m/%Y")    # Make sure the date is in the correct format 

        except ValueError:
            return "Date must be in DD/MM/YYYY format"
 
        # Update the invoice in the database 
        cursor.execute("""      
        UPDATE invoices SET customer_name=?, customer_address=?, date=?, invoice_no=?, description=?, invoice_total=?, status=?
        WHERE id=? AND user_id=?
        """, (

            customer_name,
            customer_address,
            date,
            invoice_no,
            description,
            invoice_total,
            status,
            id,
            session["user_id"]      # Makes sure that the invoice belongs to the logged in user
        ))

        conn.commit()   # Saves the changes and closes the connection to the database
        conn.close()

        return redirect("/")    # Redirect user back to the home page
 
    conn.close()

    return render_template("edit.html", invoice=invoice)
 
# Run the server

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

 