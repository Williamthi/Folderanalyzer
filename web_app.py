from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from folder_analyzer import FolderAnalyzer
import os
from pathlib import Path
import threading

app = Flask(__name__)
CORS(app)

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
            'progress': self.get_progress()
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
            return jsonify(results)
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
        return jsonify(progress)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    Path('templates').mkdir(exist_ok=True)
    # Run without exposing debug PIN
    app.run(debug=True, port=5000, use_debugger=False) 