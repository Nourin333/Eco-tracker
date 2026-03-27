import sqlite3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = "super_secret_eco_key"
DB_PATH = "database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Emissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            month TEXT,
            electricity_units REAL,
            petrol_litres REAL,
            total_co2 REAL,
            carbon_saved REAL,
            credits REAL,
            FOREIGN KEY (user_id) REFERENCES Users (id)
        )
    ''')
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/input', methods=['GET'])
@login_required
def input_page():
    return render_template('input.html')

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard_page():
    return render_template('dashboard.html')

# API Routes
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        return jsonify({"message": "Registration successful"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM Users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user[0]
        session['user_name'] = user[1]
        return jsonify({"message": "Login successful"}), 200
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200

@app.route('/api/submit-data', methods=['POST'])
@login_required
def api_submit_data():
    data = request.get_json()
    user_id = session['user_id']
    month = data.get('month') or datetime.now().strftime('%Y-%m')
    
    electricity_units = data.get('electricity_units')
    petrol_litres = data.get('petrol_litres')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we should use last month's data
    if electricity_units is None or petrol_litres is None or str(electricity_units).strip() == "" or str(petrol_litres).strip() == "":
        cursor.execute("SELECT electricity_units, petrol_litres FROM Emissions WHERE user_id = ? ORDER BY month DESC LIMIT 1", (user_id,))
        last_entry = cursor.fetchone()
        if last_entry:
            electricity_units = last_entry[0] if (electricity_units is None or str(electricity_units).strip() == "") else electricity_units
            petrol_litres = last_entry[1] if (petrol_litres is None or str(petrol_litres).strip() == "") else petrol_litres
        else:
            electricity_units = electricity_units or 0
            petrol_litres = petrol_litres or 0
            
    electricity_units = float(electricity_units)
    petrol_litres = float(petrol_litres)
    
    # Logic based on requirements
    electricity_co2 = electricity_units * 0.82
    petrol_monthly = petrol_litres * 4
    petrol_co2 = petrol_monthly * 2.31
    total_co2 = electricity_co2 + petrol_co2
    baseline = 500
    carbon_saved = baseline - total_co2
    credits = carbon_saved / 1000
    
    # Save or update for the month
    cursor.execute("SELECT id FROM Emissions WHERE user_id = ? AND month = ?", (user_id, month))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
            UPDATE Emissions 
            SET electricity_units=?, petrol_litres=?, total_co2=?, carbon_saved=?, credits=?
            WHERE id=?
        """, (electricity_units, petrol_litres, total_co2, carbon_saved, credits, existing[0]))
    else:
        cursor.execute("""
            INSERT INTO Emissions (user_id, month, electricity_units, petrol_litres, total_co2, carbon_saved, credits)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, month, electricity_units, petrol_litres, total_co2, carbon_saved, credits))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "message": "Data submitted successfully",
        "calculations": {
            "total_co2": total_co2,
            "carbon_saved": carbon_saved,
            "credits": credits
        }
    }), 200

@app.route('/api/get-dashboard', methods=['GET'])
@login_required
def api_get_dashboard():
    user_id = session['user_id']
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(total_co2), SUM(carbon_saved), SUM(credits) FROM Emissions WHERE user_id = ?", (user_id,))
    totals = cursor.fetchone()
    
    cursor.execute("SELECT month, total_co2, carbon_saved, credits FROM Emissions WHERE user_id = ? ORDER BY month DESC LIMIT 1", (user_id,))
    latest = cursor.fetchone()
    
    conn.close()
    
    total_co2 = totals[0] or 0
    total_carbon_saved = totals[1] or 0
    total_credits = totals[2] or 0
    wallet_value = total_credits * 800  # 800 INR per credit
    
    return jsonify({
        "user_name": session.get('user_name'),
        "lifetime": {
            "total_co2": round(total_co2, 2),
            "carbon_saved": round(total_carbon_saved, 2),
            "credits": round(total_credits, 2),
            "wallet_value": round(wallet_value, 2)
        },
        "latest_month": {
            "month": latest[0] if latest else None,
            "total_co2": round(latest[1], 2) if latest else 0,
            "carbon_saved": round(latest[2], 2) if latest else 0,
            "credits": round(latest[3], 2) if latest else 0
        } if latest else None
    }), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
