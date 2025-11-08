import os
import time
import shutil
import mimetypes
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
import sys
import google.generativeai as genai
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

class SmartFileOrganizer(FileSystemEventHandler):
    def __init__(self, watch_folder):
        self.watch_folder = Path(watch_folder)
        self.categories = {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'],
            'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
            'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
            'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.tex'],
            'Spreadsheets': ['.xls', '.xlsx', '.csv', '.ods'],
            'Presentations': ['.ppt', '.pptx', '.odp', '.key'],
            'Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', 
                    '.php', '.rb', '.go', '.rs', '.ts', '.jsx', '.tsx', '.vue', 
                    '.swift', '.kt', '.sql', '.sh', '.bash', '.json', '.xml', '.yaml', '.yml'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
            'Executables': ['.exe', '.msi', '.app', '.dmg', '.deb', '.rpm'],
            'Databases': ['.db', '.sqlite', '.sql', '.mdb'],
            'Fonts': ['.ttf', '.otf', '.woff', '.woff2'],
            'CAD': ['.dwg', '.dxf', '.stl', '.obj'],
        }
        
    def get_ai_category(self, file_path):
        """Use Gemini AI to intelligently categorize ambiguous files"""
        try:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            prompt = f"""Analyze this file and suggest the best category for organization:
                    
        Filename: {file_name}
        Extension: {file_ext}

        Available categories: Images, Videos, Audio, Documents, Spreadsheets, Presentations, Code, 
        Archives, Executables, Databases, Fonts, CAD, Design, 3D Models, Ebooks, Notes, Scripts, 
        Configuration, Logs, Backups, Temporary, Other

        Consider:
        1. File extension and type
        2. Filename patterns (e.g., 'backup_', 'temp_', 'config_')
        3. Common use cases

        Respond with ONLY the category name, nothing else."""

            response = model.generate_content(prompt)
            category = response.text.strip()
            
            # Validate the category
            valid_categories = list(self.categories.keys()) + [
                'Design', '3D Models', 'Ebooks', 'Notes', 'Scripts', 
                'Configuration', 'Logs', 'Backups', 'Temporary', 'Other'
            ]
            
            if category in valid_categories:
                return category
            else:
                return 'Other'
                
        except Exception as e:
            print(f"AI categorization error: {e}")
            return 'Other'
    
    def get_category(self, file_path):
        """Determine file category based on extension or AI"""
        ext = os.path.splitext(file_path)[1].lower()
        
        # Check predefined categories
        for category, extensions in self.categories.items():
            if ext in extensions:
                return category
        
        # Use AI for unknown files
        return self.get_ai_category(file_path)
    
    def organize_file(self, file_path):
        """Move file to appropriate category folder"""
        try:
            if not os.path.exists(file_path):
                return
            
            # Skip if it's a directory or hidden file
            if os.path.isdir(file_path) or os.path.basename(file_path).startswith('.'):
                return
            
            # Get category
            category = self.get_category(file_path)
            
            # Create category folder if it doesn't exist
            category_folder = self.watch_folder / category
            category_folder.mkdir(exist_ok=True)
            
            # Move file
            file_name = os.path.basename(file_path)
            destination = category_folder / file_name
            
            # Handle duplicate names
            counter = 1
            while destination.exists():
                name, ext = os.path.splitext(file_name)
                destination = category_folder / f"{name}_{counter}{ext}"
                counter += 1
            
            shutil.move(file_path, destination)
            print(f"✓ Organized: {file_name} → {category}/")
            
        except Exception as e:
            print(f"✗ Error organizing {file_path}: {e}")
    
    def on_created(self, event):
        """Handle new file creation"""
        if not event.is_directory:
            time.sleep(1)  # Wait for file to be fully written
            self.organize_file(event.src_path)
    
    def on_modified(self, event):
        """Handle file modification (optional)"""
        pass
    
    def organize_existing_files(self):
        """Organize all existing files in the folder"""
        print("🔍 Scanning existing files...")
        files = [f for f in self.watch_folder.iterdir() if f.is_file() and not f.name.startswith('.')]
        
        for file_path in files:
            self.organize_file(str(file_path))
        
        print(f"✓ Organized {len(files)} existing files")


def main():
    WATCH_FOLDER = sys.argv[1] if len(sys.argv) > 1 else "."
    
    Path(WATCH_FOLDER).mkdir(exist_ok=True)
    
    print("=" * 60)
    print("🤖 Smart File Organizer with Gemini AI")
    print("=" * 60)
    print(f"📁 Monitoring: {os.path.abspath(WATCH_FOLDER)}")
    print("🔧 Press Ctrl+C to stop")
    print("=" * 60)
    
    organizer = SmartFileOrganizer(WATCH_FOLDER)
    organizer.organize_existing_files()
    
    observer = Observer()
    observer.schedule(organizer, WATCH_FOLDER, recursive=False)
    observer.start()
    
    print("\n👀 Watching for new files...\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n\n⏹️  File organizer stopped")
    
    observer.join()


if __name__ == "__main__":
    main()