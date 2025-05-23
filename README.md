# Folder Analyzer

A Python web application that analyzes folders and provides detailed information about their contents, with a modern web interface and smart handling of cloud storage.

## Features

- 🌐 Modern web interface with real-time progress tracking
- 📊 Recursive folder scanning
- 📁 File type detection using MIME types
- 💾 File size analysis with human-readable formats
- 🕒 Most recently modified files tracking
- 📑 File type distribution statistics
- 🔍 Text file content preview with encoding detection
- ⚡ Smart cloud storage handling (OneDrive, Dropbox, etc.)
- 📝 Analysis history with quick access to previous folders
- ⚠️ Intelligent warnings for potential issues
- ❌ Analysis cancellation support

## Safety Features

- 🛡️ Size limits (max 50GB total)
- ⏱️ Time limits (max 15 minutes)
- 📄 File count limits (max 10,000 files)
- ☁️ Cloud storage protection:
  - Skips files larger than 10MB in cloud folders
  - Prevents unwanted large downloads
  - Shows warnings for cloud storage operations

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Williamthi/Folderanalyzer.git
cd Folderanalyzer
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

Note: On Windows, you might need to install additional dependencies for python-magic:
- Download and install the Windows DLL from [here](https://github.com/nscaife/file-windows/releases)
- Add the DLL directory to your system PATH

## Usage

1. Start the web server:
```bash
python web_app.py
```

2. Open your browser and go to:
```
http://localhost:5000
```

3. Enter a folder path and click "Analyze"

## Features Guide

### Basic Analysis
- Enter any folder path to analyze
- View real-time progress with detailed status
- Cancel analysis at any time if needed

### Cloud Storage Support
- Safely analyze OneDrive, Dropbox, and other cloud storage folders
- Smart size limits prevent unwanted downloads
- Clear warnings about skipped files

### History Feature
- Recently analyzed folders are saved locally
- Quick access to previous analyses
- History is not included in Git (stays private)

## Output

The analysis provides:
1. Project type detection
2. Total number of files and combined size
3. Distribution of file types
4. Top 10 largest files
5. Top 10 most recently modified files
6. Content analysis and grouping
7. Warnings and potential issues

## Requirements

- Python 3.6+
- Modern web browser
- Dependencies listed in requirements.txt

## Docker

The application can also be run as a docker image. See [`docker-compose.yml`](./docker-compose.yml) for an example usage. Mount the volumes you'd like to browse in the docker container and start it with

```sh
docker compose up
```

## Privacy Note

The folder history feature stores data locally and is not included in Git commits. The `.gitignore` file ensures your analysis history remains private. 
