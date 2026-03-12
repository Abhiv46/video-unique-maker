import os
import uuid
import time
import subprocess
from flask import Flask, request, render_template, send_file, jsonify, url_for
from werkzeug.utils import secure_filename
import moviepy.editor as mp
from PIL import Image
import numpy as np

# Flask app initialize karte hain
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here-change-it'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB limit
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'}

# Upload folder create karte hain agar exist nahi karta
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def make_video_unique(input_path, output_path):
    """
    Video ko unique banane ke liye multiple transformations
    """
    try:
        print(f"Processing video: {input_path}")
        
        # Video load karte hain
        video = mp.VideoFileClip(input_path)
        
        # 1. VIDEO TRANSFORMATIONS
        print("Applying video transformations...")
        
        # Thoda sa crop (2% border remove)
        video = video.fx(mp.vfx.crop, x_center=0.5, y_center=0.5, 
                         width=video.w*0.98, height=video.h*0.98)
        
        # Speed me thoda modification (1% fast)
        video = video.fx(mp.vfx.speedx, 1.01)
        
        # Colors me thoda adjustment
        video = video.fx(mp.vfx.colorx, 1.02)
        
        # 2. AUDIO TRANSFORMATIONS (agar audio hai to)
        if video.audio is not None:
            print("Applying audio transformations...")
            # Audio volume thoda adjust
            audio = video.audio.volumex(1.05)
            # Audio ko video ke saath set karte hain
            video = video.set_audio(audio)
        
        # 3. WATERMARK ADD KARTE HAIN (optional - apna logo)
        # Aap chahe to apna logo bhi add kar sakte ho
        # logo_path = 'logo.png'  # Agar logo file hai to
        # if os.path.exists(logo_path):
        #     logo = mp.ImageClip(logo_path).resize(height=50).set_duration(video.duration)
        #     logo = logo.set_position(('right', 'bottom')).set_start(0)
        #     video = mp.CompositeVideoClip([video, logo])
        
        # 4. FINAL VIDEO BANATE HAIN
        print("Rendering final video...")
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=video.fps,
            preset='medium',
            bitrate='2000k'
        )
        
        # Cleanup
        video.close()
        
        # 5. METADATA REMOVE KARTE HAIN (ffmpeg se)
        try:
            print("Removing metadata...")
            temp_output = output_path + '_temp.mp4'
            # FFmpeg command - metadata hatao
            cmd = [
                'ffmpeg', '-i', output_path,
                '-map_metadata', '-1',
                '-map_chapters', '-1',
                '-metadata', 'title=',
                '-metadata', 'artist=',
                '-metadata', 'comment=Created by Video Unique Maker',
                '-codec', 'copy',
                temp_output
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Old file replace karo
            os.replace(temp_output, output_path)
            print("Metadata removed successfully")
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg metadata removal failed: {e}")
        except FileNotFoundError:
            print("FFmpeg not installed, skipping metadata removal")
        
        print(f"Video processed successfully: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error in video processing: {str(e)}")
        return False

def cleanup_old_files():
    """Delete files older than 1 hour"""
    try:
        current_time = time.time()
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                # 1 hour = 3600 seconds
                if current_time - os.path.getmtime(filepath) > 3600:
                    os.remove(filepath)
                    print(f"Deleted old file: {filename}")
    except Exception as e:
        print(f"Cleanup error: {e}")

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload and process video"""
    
    # Cleanup old files
    cleanup_old_files()
    
    # Check if file exists
    if 'video' not in request.files:
        return jsonify({'error': 'कोई फाइल अपलोड नहीं हुई'}), 400
    
    file = request.files['video']
    
    if file.filename == '':
        return jsonify({'error': 'कोई फाइल सेलेक्ट नहीं की गई'}), 400
    
    # Check file type
    if not allowed_file(file.filename):
        return jsonify({'error': 'गलत फाइल फॉर्मेट। केवल वीडियो फाइल्स अलाउड हैं'}), 400
    
    try:
        # Generate unique filenames
        unique_id = str(uuid.uuid4())
        original_filename = secure_filename(file.filename)
        input_filename = f"input_{unique_id}_{original_filename}"
        output_filename = f"output_{unique_id}_{original_filename}"
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # Save uploaded file
        file.save(input_path)
        print(f"File saved: {input_path}")
        
        # Get file size
        file_size = os.path.getsize(input_path) / (1024 * 1024)  # MB mein
        
        # Process video
        success = make_video_unique(input_path, output_path)
        
        if success and os.path.exists(output_path):
            # Get output file size
            output_size = os.path.getsize(output_path) / (1024 * 1024)
            
            return jsonify({
                'success': True,
                'message': 'वीडियो सफलतापूर्वक प्रोसेस हुआ',
                'download_url': url_for('download_file', filename=output_filename),
                'original_size': f"{file_size:.2f} MB",
                'new_size': f"{output_size:.2f} MB"
            })
        else:
            return jsonify({'error': 'वीडियो प्रोसेसिंग में गलती हुई'}), 500
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({'error': f'गलती: {str(e)}'}), 500
    
    finally:
        # Input file delete kar do (optional)
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except:
            pass

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed file"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'फाइल नहीं मिली'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name='unique_video.mp4',
            mimetype='video/mp4'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a file"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
