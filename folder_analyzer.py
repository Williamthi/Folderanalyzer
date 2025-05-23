import os
import magic
from datetime import datetime
from pathlib import Path
import chardet
import re
from collections import defaultdict
import ast
import mimetypes
import time

class FolderAnalyzer:
    # Maximum limits
    MAX_FILES = 10000  # Maximum number of files to analyze
    MAX_SIZE_GB = 50   # Maximum total size in GB to analyze
    MAX_TIME_SECONDS = 900  # Maximum analysis time (15 minutes)
    MAX_CLOUD_FILE_SIZE_MB = 10  # Maximum size for cloud storage files (10MB)

    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.stats = {
            'total_files': 0,
            'total_size': 0,
            'file_types': {},
            'largest_files': [],
            'newest_files': [],
            'project_type': None,
            'content_groups': defaultdict(list),
            'dependencies': set(),
            'related_files': defaultdict(list),
            'progress': {
                'current': 0,
                'total': 0,
                'current_file': '',
                'stage': 'Initializing',
                'start_time': None,
                'elapsed_time': 0,
                'warnings': []
            }
        }
        self.mime = magic.Magic(mime=True)
        self.project_indicators = {
            'python': ['requirements.txt', 'setup.py', 'pyproject.toml'],
            'node': ['package.json', 'node_modules'],
            'web': ['index.html', 'style.css'],
            'java': ['pom.xml', 'build.gradle'],
            'docker': ['Dockerfile', 'docker-compose.yml']
        }
        self.total_size = 0
        self.start_time = None
        self.is_cloud_storage = self.check_if_cloud_storage(root_path)

    def check_if_cloud_storage(self, path):
        """Check if path is in a cloud storage folder."""
        cloud_indicators = [
            'OneDrive',
            'Dropbox',
            'Google Drive',
            'iCloudDrive',
            'Box'
        ]
        path_str = str(path).lower()
        return any(indicator.lower() in path_str for indicator in cloud_indicators)

    def should_skip_file(self, file_path):
        """Determine if a file should be skipped."""
        try:
            # Skip if file is a symlink
            if file_path.is_symlink():
                return True

            # Check if file exists and is readable
            if not file_path.exists() or not os.access(file_path, os.R_OK):
                return True

            # Get file size
            try:
                file_size = file_path.stat().st_size
            except (OSError, IOError):
                # If we can't get the size, skip the file
                self.stats['progress']['warnings'].append(f"Cannot access file: {file_path}")
                return True

            # Special handling for cloud storage files
            if self.is_cloud_storage:
                # Skip large files in cloud storage to prevent long downloads
                if file_size > (self.MAX_CLOUD_FILE_SIZE_MB * 1024 * 1024):
                    self.stats['progress']['warnings'].append(
                        f"Skipping large cloud file ({self.human_size(file_size)}): {file_path}"
                    )
                    return True

            # Check overall size limit
            if self.total_size + file_size > (self.MAX_SIZE_GB * 1024 * 1024 * 1024):
                self.stats['progress']['warnings'].append(f"Size limit reached ({self.MAX_SIZE_GB}GB)")
                return True

            self.total_size += file_size
            return False
        except Exception as e:
            self.stats['progress']['warnings'].append(f"Error accessing {file_path}: {str(e)}")
            return True

    def update_progress(self, stage, current=None, total=None, current_file=None):
        """Update the progress information."""
        if current is not None:
            self.stats['progress']['current'] = current
        if total is not None:
            self.stats['progress']['total'] = total
        if current_file is not None:
            self.stats['progress']['current_file'] = current_file
        self.stats['progress']['stage'] = stage
        
        if self.stats['progress']['start_time'] is not None:
            self.stats['progress']['elapsed_time'] = time.time() - self.stats['progress']['start_time']

    def get_progress(self):
        """Get the current progress information."""
        progress = self.stats['progress'].copy()
        if progress['total'] > 0:
            progress['percentage'] = (progress['current'] / progress['total']) * 100
        else:
            progress['percentage'] = 0
        return progress

    def detect_project_type(self):
        """Detect the type of project based on key files."""
        for proj_type, indicators in self.project_indicators.items():
            if any((self.root_path / indicator).exists() for indicator in indicators):
                self.stats['project_type'] = proj_type
                return proj_type
        return 'unknown'

    def analyze_code_file(self, file_path, content):
        """Analyze code files for imports and dependencies."""
        file_ext = file_path.suffix.lower()
        deps = set()

        if file_ext == '.py':
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        deps.update(name.name for name in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        deps.add(node.module)
            except:
                pass
        elif file_ext in ['.js', '.ts']:
            # Look for import/require statements
            import_patterns = [
                r'import\s+.*?from\s+[\'"](.+?)[\'"]',
                r'require\([\'"](.+?)[\'"]\)'
            ]
            for pattern in import_patterns:
                deps.update(re.findall(pattern, content))

        return deps

    def group_related_files(self, file_path, content_type):
        """Group related files based on naming and content type."""
        stem = file_path.stem
        parent = file_path.parent.name
        
        # Group by common prefixes
        for existing_path in self.stats['related_files']:
            existing_stem = Path(existing_path).stem
            if (stem in existing_stem or existing_stem in stem) and len(stem) > 3:
                self.stats['related_files'][existing_path].append(str(file_path))
                return

        # New group
        self.stats['related_files'][str(file_path)] = []

    def analyze_content(self, file_path, content_type):
        """Analyze file content based on its type."""
        try:
            if 'text' not in content_type and 'application' not in content_type:
                return {'type': 'binary', 'summary': 'Binary file'}

            with open(file_path, 'rb') as f:
                raw_data = f.read(1024 * 1024)  # Read first 1MB
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'

            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

            analysis = {
                'type': content_type,
                'encoding': encoding,
                'size': len(content),
                'lines': len(content.splitlines())
            }

            # Code analysis
            if any(ext in file_path.suffix.lower() for ext in ['.py', '.js', '.java', '.cpp', '.ts']):
                deps = self.analyze_code_file(file_path, content)
                analysis['dependencies'] = list(deps)
                self.stats['dependencies'].update(deps)

            # Configuration files
            elif file_path.suffix.lower() in ['.json', '.yaml', '.yml', '.toml']:
                analysis['config_type'] = 'configuration'
                if file_path.name in ['package.json', 'requirements.txt', 'pyproject.toml']:
                    analysis['purpose'] = 'dependency_management'

            # Documentation
            elif file_path.suffix.lower() in ['.md', '.rst', '.txt']:
                analysis['doc_type'] = 'documentation'
                analysis['preview'] = content[:200] + '...' if len(content) > 200 else content

            return analysis

        except Exception as e:
            return {'error': str(e)}

    def get_file_info(self, file_path):
        """Get detailed information about a file."""
        stats = file_path.stat()
        size = stats.st_size
        created = datetime.fromtimestamp(stats.st_ctime)
        modified = datetime.fromtimestamp(stats.st_mtime)
        
        try:
            mime_type = self.mime.from_file(str(file_path))
        except:
            mime_type = mimetypes.guess_type(str(file_path))[0] or 'unknown'

        # Convert to relative path for display
        try:
            relative_path = str(file_path.relative_to(self.root_path))
        except ValueError:
            relative_path = str(file_path)

        file_info = {
            'path': relative_path,  # Use relative path instead of absolute
            'absolute_path': str(file_path),  # Keep absolute path for internal use
            'size': size,
            'size_human': self.human_size(size),
            'created': created,
            'modified': modified,
            'type': mime_type
        }

        # Analyze content
        content_analysis = self.analyze_content(file_path, mime_type)
        file_info.update(content_analysis)

        # Group related files
        self.group_related_files(file_path, mime_type)

        return file_info

    def scan(self):
        """Scan the folder and collect information."""
        self.start_time = time.time()
        self.stats['progress']['start_time'] = self.start_time
        self.update_progress("Detecting project type")
        
        # Add warning for cloud storage
        if self.is_cloud_storage:
            self.stats['progress']['warnings'].append(
                f"Analyzing cloud storage folder. Files larger than {self.MAX_CLOUD_FILE_SIZE_MB}MB will be skipped to prevent long downloads."
            )

        # Detect project type first
        self.stats['project_type'] = self.detect_project_type()
        
        # Count total files first
        self.update_progress("Counting files")
        files = []
        total_files = 0
        
        for file_path in self.root_path.rglob('*'):
            if time.time() - self.start_time > self.MAX_TIME_SECONDS:
                self.stats['progress']['warnings'].append(f"Analysis timeout after {self.MAX_TIME_SECONDS} seconds")
                break
                
            if file_path.is_file() and not self.should_skip_file(file_path):
                total_files += 1
                files.append(file_path)
                
                if total_files >= self.MAX_FILES:
                    self.stats['progress']['warnings'].append(f"File limit reached ({self.MAX_FILES} files)")
                    break

        self.update_progress("Analyzing files", 0, len(files))
        
        current_file_count = 0
        for file_path in files:
            if time.time() - self.start_time > self.MAX_TIME_SECONDS:
                break
                
            current_file_count += 1
            self.update_progress(
                "Analyzing files",
                current_file_count,
                len(files),
                str(file_path.relative_to(self.root_path))
            )
            
            file_info = self.get_file_info(file_path)
            self.stats['total_files'] += 1
            self.stats['total_size'] += file_info['size']
            
            # Group by content type
            content_type = file_info.get('type', 'unknown')
            self.stats['content_groups'][content_type].append(file_info)
            
            # Track file types
            self.stats['file_types'][content_type] = self.stats['file_types'].get(content_type, 0) + 1
            
            # Track largest files
            self.stats['largest_files'].append(file_info)
            self.stats['largest_files'].sort(key=lambda x: x['size'], reverse=True)
            self.stats['largest_files'] = self.stats['largest_files'][:10]
            
            # Track newest files
            self.stats['newest_files'].append(file_info)
            self.stats['newest_files'].sort(key=lambda x: x['modified'], reverse=True)
            self.stats['newest_files'] = self.stats['newest_files'][:10]

        self.update_progress(
            "Analysis complete" if not self.stats['progress']['warnings'] else "Analysis completed with warnings",
            len(files),
            len(files)
        )

    def human_size(self, size):
        """Convert size in bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f}{unit}"
            size /= 1024
        return f"{size:.2f}PB"

    def display_results(self):
        """Display analysis results in a formatted way."""
        print("\nProject Overview")
        print(f"Project Type: {self.stats['project_type']}")
        print(f"Total Files: {self.stats['total_files']}")
        print(f"Total Size: {self.human_size(self.stats['total_size'])}")

        print("\nFile Types Distribution:")
        for file_type, count in sorted(self.stats['file_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"{file_type}: {count}")

        print("\nLargest Files:")
        for file in self.stats['largest_files']:
            print(f"{file['size_human']}: {file['path']}")

        print("\nMost Recent Files:")
        for file in self.stats['newest_files']:
            print(f"{file['modified'].strftime('%Y-%m-%d %H:%M:%S')}: {file['path']}")

def main():
    folder_path = input("Enter the folder path to analyze (press Enter for current folder): ").strip()
    if not folder_path:
        folder_path = "."
    
    try:
        analyzer = FolderAnalyzer(folder_path)
        analyzer.scan()
        analyzer.display_results()
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 