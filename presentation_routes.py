from flask import Blueprint, request, jsonify, send_file, session, render_template
from utils import login_required
from presentation_service import generate_text_content, create_presentation, generate_slide_previews
from db_models import get_db
from template_manager import TemplateManager
import os
import uuid
import logging
import base64

presentation_bp = Blueprint('presentation', __name__)
logger = logging.getLogger(__name__)
template_manager = TemplateManager()

@presentation_bp.route('/generate_ppt', methods=['POST'])
@login_required
def generate_ppt():
    try:
        data = request.json
        template = data.get('template', 'default')
        content_type = data.get('content_type', 'auto_generate')
        
        if not template_manager.get_template(template):
            return jsonify({"error": "Invalid template selected"}), 400
        
        content_data = None
        topic = None
        image_prompts = {}
        
        if content_type == 'auto_generate':
            topic = data.get('topic')
            num_slides = int(data.get('num_slides', 3))
            
            if not topic:
                return jsonify({"error": "Topic is required for auto-generated content"}), 400
            if num_slides < 1 or num_slides > 20:
                return jsonify({"error": "Number of slides must be between 1 and 20"}), 400
                
            logger.info(f"User {session['username']} generating content for topic: {topic} with {num_slides} slides using template: {template}")
            content_data = generate_text_content(topic, num_slides)
            
        elif content_type == 'custom':
            custom_content = data.get('custom_content')
            custom_title = data.get('custom_title', 'Custom Presentation')
            
            if not custom_content:
                return jsonify({"error": "Custom content is required when selecting custom content type"}), 400
                
            logger.info(f"User {session['username']} using custom content with template: {template}")
            content_data = generate_text_content(custom_title, 0, custom_content)
            topic = content_data.get("title", custom_title)
            
        else:
            return jsonify({"error": "Invalid content type"}), 400
        
        slide_count = 1 + len(content_data.get('slides', []))
        
        try:
            logger.info("Generating title image prompt")
            title_image_prompt = f"Professional presentation image related to: {topic}"
            if title_image_prompt:
                image_prompts["title"] = title_image_prompt
                
            for i, slide_data in enumerate(content_data.get("slides", [])):
                slide_title = slide_data.get("title", "")
                slide_image_prompt = f"Professional presentation image related to: {topic} - {slide_title}"
                if slide_image_prompt:
                    image_prompts[str(i)] = slide_image_prompt
        except Exception as e:
            logger.warning(f"Image prompt generation failed: {str(e)}")
            
        logger.info(f"Creating PowerPoint presentation with template: {template}")
        ppt_file, preview_data = create_presentation(content_data, image_prompts, template)
        
        unique_id = uuid.uuid4().hex[:8]
        safe_topic = topic.replace(' ', '_') if topic else 'Presentation'
        filename = f"{safe_topic}_{unique_id}.pptx"
        user_filename = os.path.join("static", "downloads", filename)
        os.makedirs(os.path.dirname(user_filename), exist_ok=True)
        with open(ppt_file, 'rb') as src, open(user_filename, 'wb') as dst:
            dst.write(src.read())
        os.unlink(ppt_file)
        
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute('''
                INSERT INTO presentations (user_id, title, filename, template, slide_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], content_data.get("title", topic), filename, template, slide_count))
            conn.commit()
            conn.close()
            logger.info(f"Saved presentation to user {session['username']}'s history")
        except Exception as e:
            logger.error(f"Failed to save presentation to history: {str(e)}")
        
        return jsonify({
            "success": True,
            "filename": filename,
            "download_url": f"/download/{filename}",
            "content": content_data,
            "image_prompts": image_prompts,
            "template": template,
            "preview_data": preview_data
        })
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@presentation_bp.route('/update_ppt', methods=['POST'])
@login_required
def update_ppt():
    try:
        data = request.json
        content_data = data.get('content')
        image_prompts = data.get('image_prompts', {})
        template = data.get('template', 'default')
        if not content_data or 'title' not in content_data or 'slides' not in content_data:
            return jsonify({"error": "Invalid presentation content"}), 400
        logger.info(f"User {session['username']} updating PowerPoint presentation")
        
        slide_count = 1 + len(content_data.get('slides', []))
        
        ppt_file, preview_data = create_presentation(content_data, image_prompts, template)
        unique_id = uuid.uuid4().hex[:8]
        topic = content_data.get("title", "Presentation").replace(' ', '_')
        filename = f"{topic}_{unique_id}.pptx"
        user_filename = os.path.join("static", "downloads", filename)
        os.makedirs(os.path.dirname(user_filename), exist_ok=True)
        with open(ppt_file, 'rb') as src, open(user_filename, 'wb') as dst:
            dst.write(src.read())
        os.unlink(ppt_file)
        
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute('''
                INSERT INTO presentations (user_id, title, filename, template, slide_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], content_data.get("title", topic), filename, template, slide_count))
            conn.commit()
            conn.close()
            logger.info(f"Saved updated presentation to user {session['username']}'s history")
        except Exception as e:
            logger.error(f"Failed to save updated presentation to history: {str(e)}")
            
        return jsonify({
            "success": True,
            "filename": filename,
            "download_url": f"/download/{filename}",
            "preview_data": preview_data
        })
    except Exception as e:
        logger.error(f"Error updating presentation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@presentation_bp.route('/view/<filename>')
@login_required
def view_file(filename):
    file_path = os.path.join("static", "downloads", filename)
    if not os.path.exists(file_path):
        logger.error(f"View file not found: {file_path}")
        return jsonify({"error": "File not found"}), 404
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM presentations WHERE user_id = ? AND filename = ?', 
             (session['user_id'], filename))
    presentation = c.fetchone()
    conn.close()
    
    if not presentation:
        logger.warning(f"User {session['username']} attempted to access unauthorized file: {filename}")
        return jsonify({"error": "Unauthorized access"}), 403
    
    try:
        # Generate slide previews
        slide_previews = generate_slide_previews(file_path)
        # Convert images to base64 for embedding in HTML
        previews_base64 = []
        for preview in slide_previews:
            image_data = preview['image'].read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            previews_base64.append({
                'title': preview['title'],
                'content': preview['content'],
                'image': f"data:image/png;base64,{image_base64}"
            })
        logger.info(f"User {session['username']} viewing presentation: {filename}")
        return render_template('view_presentation.html', 
                              presentation=presentation,
                              previews=previews_base64,
                              filename=filename)
    except Exception as e:
        logger.error(f"Error generating slide previews for {filename}: {str(e)}")
        return jsonify({"error": "Failed to generate preview"}), 500

@presentation_bp.route('/download/<filename>')
@login_required
def download_file(filename):
    file_path = os.path.join("static", "downloads", filename)
    if not os.path.exists(file_path):
        logger.error(f"Download file not found: {file_path}")
        return jsonify({"error": "File not found"}), 404
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM presentations WHERE user_id = ? AND filename = ?', 
             (session['user_id'], filename))
    presentation = c.fetchone()
    conn.close()
    
    if not presentation:
        logger.warning(f"User {session['username']} attempted to access unauthorized file: {filename}")
        return jsonify({"error": "Unauthorized access"}), 403
        
    logger.info(f"User {session['username']} downloading file: {file_path}")
    return send_file(file_path, as_attachment=True)

@presentation_bp.route('/get_templates', methods=['GET'])
def get_templates():
    try:
        templates = template_manager.get_all_templates()
        template_response = {}
        for key, template in templates.items():
            template_response[key] = {
                "name": template.get('name', key),
                "description": template.get('description', ''),
                "preview_image": template.get('preview_image', ''),
                "styles": template.get('styles', {})
            }
        logger.info(f"Returning {len(template_response)} templates")
        return jsonify({
            "success": True,
            "templates": template_response
        })
    except Exception as e:
        logger.error(f"Error retrieving templates: {str(e)}")
        return jsonify({"error": "Failed to retrieve templates"}), 500