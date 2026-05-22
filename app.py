from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from google.oauth2 import id_token
from google.auth.transport import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cgpa-calc-super-secret'

# Use environment database URL if available (for production databases like PostgreSQL), default to SQLite locally
db_url = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

GOOGLE_CLIENT_ID = "651086801146-94dj14nbm04ntbpu0c4dpm8atf1ekstd.apps.googleusercontent.com"

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    history = db.relationship('CalculationHistory', backref='user', lazy=True)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

class CalculationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cgpa = db.Column(db.Float, nullable=False)
    total_units = db.Column(db.Float, nullable=False)
    courses_data = db.Column(db.Text, nullable=True) # JSON string of courses
    date_saved = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('calculator'))
        
    if request.method == 'POST':
        login_id = request.form.get('login_id')
        password = request.form.get('password')
        
        user = User.query.filter((User.email == login_id) | (User.username == login_id)).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('calculator'))
        else:
            flash('Login details incorrect. Please try again.')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('calculator'))

    if request.method == 'POST':
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        username = request.form.get('username')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('signup'))
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already taken')
            return redirect(url_for('signup'))
            
        # Make first user admin
        is_first_user = User.query.first() is None
        
        new_user = User(
            firstname=firstname,
            lastname=lastname,
            username=username,
            phone=phone,
            email=email,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            is_admin=is_first_user
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Auto-login the new user after signup
        login_user(new_user)
        return redirect(url_for('calculator'))
    return render_template('signup.html')

@app.route('/calculator')
@login_required
def calculator():
    user_history = CalculationHistory.query.filter_by(user_id=current_user.id).order_by(CalculationHistory.date_saved.desc()).all()
    return render_template('calculator.html', history=user_history)

@app.route('/save_cgpa', methods=['POST'])
@login_required
def save_cgpa():
    data = request.get_json()
    cgpa = data.get('cgpa')
    units = data.get('units')
    courses = data.get('courses')
    import json
    courses_data_str = json.dumps(courses) if courses else None

    if cgpa is not None and units is not None:
        new_calc = CalculationHistory(user_id=current_user.id, cgpa=float(cgpa), total_units=float(units), courses_data=courses_data_str)
        db.session.add(new_calc)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Saved successfully!'})
    return jsonify({'success': False, 'message': 'Invalid data'})
    return jsonify({'success': False, 'message': 'Invalid data'})

@app.route('/google_login', methods=['POST'])
def google_login():
    data = request.get_json()
    token = data.get('credential')
    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        
        email = idinfo['email']
        firstname = idinfo.get('given_name', '')
        lastname = idinfo.get('family_name', '')
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if not user:
            # Generate a unique username based on the email
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
                
            # Make first user admin
            is_first_user = User.query.first() is None

            # Create the new user with a random secure password since they use Google Login
            user = User(
                firstname=firstname,
                lastname=lastname,
                username=username,
                email=email,
                password=generate_password_hash(os.urandom(24).hex(), method='pbkdf2:sha256'),
                is_admin=is_first_user
            )
            db.session.add(user)
            db.session.commit()
            
        login_user(user)
        return jsonify({'success': True})
    except ValueError:
        # Invalid token
        return jsonify({'success': False, 'message': 'Invalid Google token'}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/edit_history/<int:id>', methods=['POST'])
@login_required
def edit_history(id):
    history_item = CalculationHistory.query.get_or_404(id)
    if history_item.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    cgpa = data.get('cgpa')
    units = data.get('units')
    courses = data.get('courses')
    import json
    courses_data_str = json.dumps(courses) if courses else None

    if cgpa is not None and units is not None:
        history_item.cgpa = float(cgpa)
        history_item.total_units = float(units)
        if courses_data_str is not None:
            history_item.courses_data = courses_data_str
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/delete_history/<int:id>', methods=['POST'])
@login_required
def delete_history(id):
    history_item = CalculationHistory.query.get_or_404(id)
    if history_item.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    db.session.delete(history_item)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/admin')
@admin_required
def admin_dashboard():
    users = User.query.all()
    all_history = CalculationHistory.query.order_by(CalculationHistory.date_saved.desc()).all()
    
    # Group history by user_id for easier display
    history_by_user = {}
    for h in all_history:
        if h.user_id not in history_by_user:
            history_by_user[h.user_id] = []
        history_by_user[h.user_id].append(h)
        
    return render_template('admin.html', users=users, history_by_user=history_by_user, all_history=all_history)

@app.route('/admin/delete_user/<int:id>', methods=['POST'])
@admin_required
def admin_delete_user(id):
    if id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete yourself'})
        
    user = User.query.get_or_404(id)
    # Delete associated history first
    CalculationHistory.query.filter_by(user_id=id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

with app.app_context():
    db.create_all()
    # Migration: add is_admin and courses_data columns if they don't exist yet
    from sqlalchemy import text
    with db.engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL"))
            conn.commit()
            print("Migration applied: added is_admin column.")
        except Exception:
            pass  # Column already exists, nothing to do
        try:
            conn.execute(text("ALTER TABLE calculation_history ADD COLUMN courses_data TEXT"))
            conn.commit()
            print("Migration applied: added courses_data column.")
        except Exception:
            pass  # Column already exists, nothing to do

if __name__ == '__main__':
    app.run(debug=True)

