# Folder Analyzer

A Python tool that analyzes folders and provides detailed information about their contents without having to manually open each file.

## Features

- 📊 Recursive folder scanning
- 📁 File type detection using MIME types
- 💾 File size analysis with human-readable formats
- 🕒 Most recently modified files tracking
- 📑 File type distribution statistics
- 🔍 Text file content preview with encoding detection

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

Run the script:
```bash
python folder_analyzer.py
```

When prompted, enter the path of the folder you want to analyze, or press Enter to analyze the current directory.

## Output

The tool will display:
1. Total number of files and combined size
2. Distribution of file types
3. Top 10 largest files
4. Top 10 most recently modified files

## Requirements

- Python 3.6+
- Dependencies listed in requirements.txt 