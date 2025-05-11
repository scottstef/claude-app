# app/file_handler.py
import os
import base64
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename
from app.config import Config

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    """Save uploaded file and return filename and filepath"""
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    filepath = Config.UPLOADS_DIR / filename
    file.save(str(filepath))
    return filename, filepath

def encode_file_for_claude(file_path):
    """Encode file for Claude API based on file type"""
    mime_type, _ = mimetypes.guess_type(str(file_path))
    file_ext = file_path.suffix.lower()
    
    with open(file_path, 'rb') as file:
        # Handle Word documents
        if file_ext in ('.docx', '.doc'):
            try:
                from docx import Document
                document = Document(str(file_path))
                full_text = []
                for para in document.paragraphs:
                    full_text.append(para.text)
                return {
                    "type": "text",
                    "text": "\n".join(full_text)
                }
            except Exception as e:
                print(f"Error reading Word document: {e}")
                return {
                    "type": "text",
                    "text": f"Error reading Word document: {e}\n\nUnable to process the file content."
                }
        
        # Handle PDF files
        elif file_ext == '.pdf':
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(str(file_path))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return {
                    "type": "text",
                    "text": text
                }
            except Exception as e:
                print(f"Error reading PDF file: {e}")
                return {
                    "type": "text",
                    "text": f"Error reading PDF file: {e}\n\nUnable to process the file content."
                }
        
        # Handle images
        elif mime_type and mime_type.startswith('image/'):
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": base64.b64encode(file.read()).decode()
                }
            }
        else:
            # For text files, read as text
            try:
                file.seek(0)
                return {
                    "type": "text",
                    "text": file.read().decode('utf-8')
                }
            except UnicodeDecodeError:
                return {
                    "type": "text",
                    "text": "This file appears to be a binary file that cannot be processed as text."
                }