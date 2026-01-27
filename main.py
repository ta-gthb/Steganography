import os
from flask import Flask, render_template, request, send_file, jsonify
from stegano import lsb
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_message(image_path, message):
    """
    Encodes a secret message into an image using LSB steganography.
    
    Parameters:
    - image_path (str): Path to the input image
    - message (str): Message to hide in the image
    
    Returns:
    - Image object with hidden message
    """
    secret = lsb.hide(image_path, message)
    return secret

def decode_message(image_path):
    """
    Decodes a hidden message from an image.
    
    Parameters:
    - image_path (str): Path to the image with a hidden message
    
    Returns:
    - str: The hidden message or None if no message found
    """
    hidden_message = lsb.reveal(image_path)
    return hidden_message

@app.route('/')
def index():
    """Home page with options to encode or decode."""
    return render_template('index.html')

@app.route('/encode', methods=['GET', 'POST'])
def encode():
    """Encode message in image."""
    if request.method == 'POST':
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        message = request.form.get('message', '')
        
        # Validate inputs
        if image_file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        if not message:
            return jsonify({'error': 'Please enter a message to encode'}), 400
        
        if len(message) > 10000:
            return jsonify({'error': 'Message is too long (max 10000 characters)'}), 400
        
        if not allowed_file(image_file.filename):
            return jsonify({'error': 'Only .jpg, .jpeg, and .png files are allowed'}), 400
        
        try:
            # Save uploaded file
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_' + filename)
            image_file.save(filepath)
            
            # Encode message
            encoded_image = encode_message(filepath, message)
            
            # Save encoded image to bytes
            output_filename = 'encoded_' + os.path.splitext(filename)[0] + '.png'
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            encoded_image.save(output_path)
            
            # Clean up temp file
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'message': 'Message encoded successfully!',
                'download_url': f'/download/{output_filename}'
            })
        
        except Exception as e:
            return jsonify({'error': f'Error encoding message: {str(e)}'}), 500
    
    return render_template('encode.html')

@app.route('/decode', methods=['GET', 'POST'])
def decode():
    """Decode message from image."""
    if request.method == 'POST':
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        image_file = request.files['image']
        
        # Validate inputs
        if image_file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        if not allowed_file(image_file.filename):
            return jsonify({'error': 'Only .jpg, .jpeg, and .png files are allowed'}), 400
        
        try:
            # Save uploaded file
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_' + filename)
            image_file.save(filepath)
            
            # Decode message
            hidden_message = decode_message(filepath)
            
            # Clean up temp file
            os.remove(filepath)
            
            if hidden_message:
                return jsonify({
                    'success': True,
                    'message': hidden_message
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No hidden message found in this image.'
                })
        
        except Exception as e:
            return jsonify({'error': f'Error decoding message: {str(e)}'}), 500
    
    return render_template('decode.html')

@app.route('/download/<filename>')
def download(filename):
    """Download encoded image."""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Security check
    if not os.path.exists(filepath) or not filename.startswith('encoded_'):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up old files from uploads folder."""
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
        return jsonify({'success': True, 'message': 'Cleanup completed'})
    except Exception as e:
        return jsonify({'error': f'Error during cleanup: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)