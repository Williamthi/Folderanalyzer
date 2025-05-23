from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from folder_analyzer import FolderAnalyzer
import os
from pathlib import Path
import threading
import time
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Constants
HISTORY_FILE = 'folder_history.json'
MAX_HISTORY = 10  # Maximum number of folders to remember

def load_history():
    """Load folder history from file."""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_history(folder_path):
    """Save folder to history."""
    history = load_history()
    
    # Create history entry with timestamp
    entry = {
        'path': folder_path,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'name': os.path.basename(folder_path) or folder_path
    }
    
    # Remove if already exists
    history = [h for h in history if h['path'] != folder_path]
    
    # Add to front of list
    history.insert(0, entry)
    
    # Keep only MAX_HISTORY items
    history = history[:MAX_HISTORY]
    
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    except Exception:
        pass

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Global variable to store the current analyzer instance
current_analyzer = None
analysis_lock = threading.Lock()

class WebAnalyzer(FolderAnalyzer):
    def display_results(self):
        """Override display_results to return JSON data instead of console output"""
        results = {
            'project_overview': {
                'project_type': self.stats['project_type'],
                'total_files': self.stats['total_files'],
                'total_size': self.human_size(self.stats['total_size'])
            },
            'content_analysis': {},
            'related_files': {},
            'file_types': [],
            'largest_files': [],
            'newest_files': [],
            'progress': self.get_progress(),
            'warnings': self.stats['progress']['warnings']
        }

        # Content Groups
        for content_type, files in self.stats['content_groups'].items():
            results['content_analysis'][content_type] = {
                'count': len(files),
                'files': [{
                    'path': file['path'],
                    'dependencies': file.get('dependencies', [])[:5],
                    'purpose': file.get('purpose', '')
                } for file in files[:5]]
            }

        # Related Files
        for main_file, related in self.stats['related_files'].items():
            if related:
                results['related_files'][main_file] = related

        # File Types
        results['file_types'] = [
            {'type': file_type, 'count': count}
            for file_type, count in sorted(self.stats['file_types'].items(), key=lambda x: x[1], reverse=True)
        ]

        # Largest Files
        results['largest_files'] = [
            {'size': file['size_human'], 'path': file['path']}
            for file in self.stats['largest_files']
        ]

        # Newest Files
        results['newest_files'] = [
            {
                'modified': file['modified'].strftime('%Y-%m-%d %H:%M:%S'),
                'path': file['path']
            }
            for file in self.stats['newest_files']
        ]

        return results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def get_history():
    """Get the folder analysis history."""
    return jsonify(load_history())

@app.route('/analyze', methods=['POST'])
def analyze():
    global current_analyzer
    
    folder_path = request.json.get('path', '.')
    if not os.path.exists(folder_path):
        return jsonify({'error': 'Path does not exist'}), 404
    
    try:
        with analysis_lock:
            analyzer = WebAnalyzer(folder_path)
            current_analyzer = analyzer
            analyzer.scan()
            results = analyzer.display_results()
            current_analyzer = None
            
            # Save to history only if analysis was successful
            save_history(folder_path)
            
            # Check for warnings
            if analyzer.stats['progress']['warnings']:
                results['warnings'] = analyzer.stats['progress']['warnings']
                
            return jsonify(results)
    except ValueError as e:
        current_analyzer = None
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_analyzer = None
        return jsonify({'error': str(e)}), 500

@app.route('/progress')
def get_progress():
    """Get the current analysis progress."""
    if current_analyzer is None:
        return jsonify({'error': 'No analysis in progress'}), 404
    
    try:
        progress = current_analyzer.get_progress()
        if current_analyzer.stats['progress']['warnings']:
            progress['warnings'] = current_analyzer.stats['progress']['warnings']
        return jsonify(progress)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cancel', methods=['POST'])
def cancel_analysis():
    """Cancel the current analysis."""
    global current_analyzer
    if current_analyzer is not None:
        current_analyzer = None
        return jsonify({'message': 'Analysis cancelled'})
    return jsonify({'message': 'No analysis in progress'}), 404

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    Path('templates').mkdir(exist_ok=True)
    app.run(debug=True, port=5000, use_debugger=False) 