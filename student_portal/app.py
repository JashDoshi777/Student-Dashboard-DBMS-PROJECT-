from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)

# Database connection with automatic user context
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Jashdoshi7$",
            database="student_portal",
            autocommit=True
        )
        if 'user_id' in session:
            cursor = conn.cursor()
            cursor.execute("SET @current_user_id = %s", (session['user_id'],))
            cursor.execute(f"""
                CREATE OR REPLACE ALGORITHM=MERGE SQL SECURITY DEFINER VIEW current_user_data AS
                SELECT * FROM students WHERE user_id = {session['user_id']}
            """)
            cursor.close()
        return conn
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", 'danger')
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def dashboard():
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('login'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM current_user_data")
        students = cursor.fetchall()
        return render_template('dashboard.html', students=students)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return render_template('dashboard.html', students=[])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        grade = request.form.get('grade')
        student_id = request.form.get('student_id')
        
        if not all([name, age, grade]):
            flash('Name, age and grade are required', 'danger')
            return redirect(url_for('add_student'))

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO students (name, age, grade, student_id, user_id) VALUES (%s, %s, %s, %s, %s)",
                (name, age, grade, student_id, session['user_id'])
            )
            # Refresh the view
            cursor.execute(f"""
                CREATE OR REPLACE VIEW current_user_data AS
                SELECT * FROM students WHERE user_id = {session['user_id']}
            """)
            flash('Student added successfully!', 'success')
            return redirect(url_for('dashboard'))
        except mysql.connector.IntegrityError:
            flash('Student ID already exists', 'danger')
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('add_student.html')

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    conn = get_db_connection()
    if not conn:
        return redirect(url_for('dashboard'))

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM current_user_data WHERE id = %s
        """, (student_id,))
        student = cursor.fetchone()
        
        if not student:
            flash('Student not found or access denied', 'danger')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            name = request.form.get('name')
            age = request.form.get('age')
            grade = request.form.get('grade')
            new_student_id = request.form.get('student_id')
            
            if new_student_id != student['student_id']:
                cursor.execute("""
                    SELECT id FROM students 
                    WHERE student_id = %s AND user_id = %s AND id != %s
                """, (new_student_id, session['user_id'], student_id))
                if cursor.fetchone():
                    flash('Student ID already exists', 'danger')
                    return redirect(url_for('edit_student', student_id=student_id))
            
            cursor.execute("""
                UPDATE students 
                SET name=%s, age=%s, grade=%s, student_id=%s 
                WHERE id=%s AND user_id=%s
            """, (name, age, grade, new_student_id, student_id, session['user_id']))
            
            # Refresh the view
            cursor.execute(f"""
                CREATE OR REPLACE VIEW current_user_data AS
                SELECT * FROM students WHERE user_id = {session['user_id']}
            """)
            
            flash('Student updated!', 'success')
            return redirect(url_for('dashboard'))
        
        return render_template('edit_student.html', student=student)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/delete_student/<int:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM students 
            WHERE id=%s AND user_id=%s
        """, (student_id, session['user_id']))
        
        if cursor.rowcount == 0:
            flash('Student not found or access denied', 'danger')
        else:
            # Refresh the view
            cursor.execute(f"""
                CREATE OR REPLACE VIEW current_user_data AS
                SELECT * FROM students WHERE user_id = {session['user_id']}
            """)
            flash('Student deleted!', 'success')
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['username'] = username
                session['user_id'] = user['id']
                
                # Set up automatic filtering
                cursor.execute("SET @current_user_id = %s", (user['id'],))
                cursor.execute(f"""
                    CREATE OR REPLACE ALGORITHM=MERGE SQL SECURITY DEFINER VIEW current_user_data AS
                    SELECT * FROM students WHERE user_id = {user['id']}
                """)
                conn.commit()
                
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                flash('Username already exists', 'danger')
                return redirect(url_for('register'))

            hashed_pw = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_pw)
            )
            flash('Registration successful! Please login', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DROP VIEW IF EXISTS current_user_data")
        conn.commit()
    except:
        pass
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)