from werkzeug.security import generate_password_hash, check_password_hash
from db_models import get_db
import logging

logger = logging.getLogger(__name__)

def register_user(username, email, password, confirm_password):
    if not username or not email or not password:
        return None, None, 'All fields are required'
        
    if password != confirm_password:
        return None, None, 'Passwords do not match'
        
    if len(password) < 6:
        return None, None, 'Password must be at least 6 characters'
    
    hashed_password = generate_password_hash(password)
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
        existing_user = c.fetchone()
        
        if existing_user:
            conn.close()
            return None, None, 'Username or email already exists'
            
        c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                 (username, email, hashed_password))
        conn.commit()
        
        c.execute('SELECT id, username FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        
        return user['id'], user['username'], None
    except Exception as e:
        logger.error(f"Database error during registration: {str(e)}")
        return None, None, 'An error occurred. Please try again.'

def login_user(email, password):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            return user['id'], user['username'], None
        else:
            return None, None, 'Invalid email or password'
    except Exception as e:
        logger.error(f"Database error during login: {str(e)}")
        return None, None, 'An error occurred. Please try again.'