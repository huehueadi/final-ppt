
from flask import Blueprint, render_template, request, redirect, url_for, session
from auth_service import register_user, login_user
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('profile.dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        try:
            user_id, username, error = register_user(username, email, password, confirm_password)
            if error:
                return render_template('register.html', error=error)
            session['user_id'] = user_id
            session['username'] = username
            logger.debug(f"User registered: user_id={user_id}, username={username}, session={session}")
            return redirect(url_for('profile.dashboard'))
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return render_template('register.html', error='An error occurred. Please try again.')
            
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('profile.dashboard'))
        
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            user_id, username, error = login_user(email, password)
            if error:
                return render_template('login.html', error=error)
            session['user_id'] = user_id
            session['username'] = username
            logger.debug(f"User logged in: user_id={user_id}, username={username}, session={session}")
            return redirect(url_for('profile.dashboard'))
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return render_template('login.html', error='An error occurred. Please try again.')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    logger.debug("User logged out")
    return redirect(url_for('auth.login'))
