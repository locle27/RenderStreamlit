from flask import Flask, render_template, jsonify, request
import json
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

@app.route('/templates')
def get_templates_page():
    """Trả về trang HTML cho quản lý templates"""
    return render_template('templates.html')

@app.route('/api/templates')
def get_templates_api():
    """API endpoint trả về JSON data của templates"""
    templates_path = BASE_DIR / 'message_templates.json'
    try:
        if not templates_path.exists():
            return jsonify([])
            
        with open(templates_path, 'r', encoding='utf-8') as f:
            templates = json.load(f)
            
        if not isinstance(templates, list):
            return jsonify([])
            
        valid_templates = []
        for template in templates:
            if isinstance(template, dict) and 'Category' in template:
                valid_templates.append(template)
        
        return jsonify(valid_templates)
        
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify([])
    except Exception as e:
        print(f"Error: {e}")
        return jsonify([])

@app.route('/api/templates/debug')
def debug_templates():
    """Debug endpoint to check templates data"""
    templates_path = BASE_DIR / 'message_templates.json'
    
    debug_info = {
        'file_exists': templates_path.exists(),
        'file_path': str(templates_path),
        'file_size': templates_path.stat().st_size if templates_path.exists() else 0,
        'templates_count': 0,
        'sample_template': None,
        'error': None
    }
    
    try:
        if templates_path.exists():
            with open(templates_path, 'r', encoding='utf-8') as f:
                content = f.read()
                debug_info['file_content_length'] = len(content)
                
                templates = json.loads(content)
                debug_info['templates_count'] = len(templates)
                debug_info['templates_type'] = type(templates).__name__
                
                if templates:
                    debug_info['sample_template'] = templates[0]
                    debug_info['all_categories'] = list(set(t.get('Category', 'NO_CATEGORY') for t in templates))
                    
    except Exception as e:
        debug_info['error'] = str(e)
        
    return jsonify(debug_info)

@app.route('/api/save_templates', methods=['POST'])
def save_templates_api():
    templates_path = BASE_DIR / 'message_templates.json'
    templates = request.get_json()
    try:
        with open(templates_path, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False, indent=4)
        return jsonify({'success': True, 'message': 'Đã lưu các mẫu tin nhắn.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/templates/import')
def import_templates():
    return jsonify({'success': True, 'message': 'Import thành công (demo mode)'})

@app.route('/templates/export')
def export_templates():
    return jsonify({'success': True, 'message': 'Export thành công (demo mode)'})

if __name__ == '__main__':
    app.run(debug=True, port=5002)
