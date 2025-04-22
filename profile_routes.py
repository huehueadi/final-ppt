from flask import Blueprint, render_template, session, redirect, url_for, jsonify, flash
from utils import login_required
from db_models import get_db
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

profile_bp = Blueprint('profile', __name__)
logger = logging.getLogger(__name__)

@profile_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM presentations WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],))
        presentations = c.fetchall()
        conn.close()

        presentation_list = []
        for pres in presentations:
            pres_dict = dict(pres)
            if isinstance(pres_dict['created_at'], str):
                pres_dict['created_at'] = datetime.strptime(pres_dict['created_at'], "%Y-%m-%d %H:%M:%S")
            presentation_list.append(pres_dict)

        from template_manager import TemplateManager
        template_manager = TemplateManager()
        templates = template_manager.get_all_templates()
        template_list = []
        for key, template in templates.items():
            template_list.append({
                "id": key,
                "name": template.get('name', key),
                "description": template.get('description', ''),
                "preview_image": template.get('preview_image', '')
            })
        
        return render_template('dashboard.html', 
                              username=session['username'], 
                              presentations=presentation_list,
                              templates=template_list)
    except Exception as e:
        logger.error(f"Dashboard route error: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('auth.login'))

@profile_bp.route('/profile')
@login_required
def profile():
    try:
        user_id = int(session['user_id'])
        logger.debug(f"Fetching profile for user_id: {user_id}")
        conn = get_db()
        c = conn.cursor()
        
        # Fetch user data
        c.execute('SELECT username, email, created_at FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        logger.debug(f"User query result: {user}")
        if not user:
            logger.warning(f"User not found for user_id: {user_id}")
            flash('User not found.', 'error')
            return redirect(url_for('auth.login'))
        if not user['username']:
            logger.warning(f"Invalid username for user_id: {user_id}")
            flash('Invalid username.', 'error')
            return redirect(url_for('profile.dashboard'))
        user = {'username': user['username'], 'email': user['email'], 'created_at': user['created_at']}
        
        # Fetch total presentation count
        c.execute('SELECT COUNT(*) as count FROM presentations WHERE user_id = ?', (user_id,))
        presentation_count = c.fetchone()['count']
        logger.debug(f"Total presentations: {presentation_count}")
        
        # Fetch monthly count
        month_start = datetime.now() - relativedelta(months=1)
        c.execute('SELECT COUNT(*) as count FROM presentations WHERE user_id = ? AND created_at >= ?', 
                  (user_id, month_start))
        presentations_this_month = c.fetchone()['count']
        logger.debug(f"Presentations this month: {presentations_this_month}")
        
        # Fetch weekly count
        week_start = datetime.now() - relativedelta(days=7)
        c.execute('SELECT COUNT(*) as count FROM presentations WHERE user_id = ? AND created_at >= ?', 
                  (user_id, week_start))
        presentations_this_week = c.fetchone()['count']
        logger.debug(f"Presentations this week: {presentations_this_week}")
        
        # Fetch graph data
        c.execute('SELECT DATE(created_at) as date, COUNT(*) as count FROM presentations WHERE user_id = ? AND created_at >= ? GROUP BY DATE(created_at)', 
                  (user_id, month_start))
        graph_data_raw = c.fetchall()
        graph_data = [{'date': row['date'], 'count': row['count']} for row in graph_data_raw]
        logger.debug(f"Graph data: {graph_data}")
        
        # Fetch recent presentations with filename
        c.execute('SELECT id, title, created_at, slide_count, filename FROM presentations WHERE user_id = ? ORDER BY created_at DESC LIMIT 3', 
                  (user_id,))
        recent_presentations = c.fetchall()
        logger.debug(f"Recent presentations: {recent_presentations}")
        
        conn.close()
        
        return render_template('profile.html', 
                              user=user, 
                              presentation_count=presentation_count,
                              presentations_this_month=presentations_this_month,
                              presentations_this_week=presentations_this_week,
                              graph_data=graph_data,
                              recent_presentations=recent_presentations)
    except Exception as e:
        logger.error(f"Profile route error: {str(e)}")
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect(url_for('profile.dashboard'))

@profile_bp.route('/user/history')
@login_required
def user_history():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM presentations WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],))
        presentations = c.fetchall()
        conn.close()
        
        return jsonify({
            "success": True,
            "history": [{
                "id": p['id'],
                "title": p['title'],
                "filename": p['filename'],
                "template": p['template'],
                "slide_count": p['slide_count'],
                "created_at": p['created_at'],
                "download_url": f"/download/{p['filename']}"
            } for p in presentations]
        })
    except Exception as e:
        logger.error(f"User history route error: {str(e)}")
        return jsonify({"error": str(e)}), 500