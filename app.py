from flask import Flask, request, send_file, redirect, url_for, render_template
from rembg import remove
from PIL import Image, ImageEnhance
import os
import csv
import requests
from io import BytesIO
import zipfile

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

processed_images = set()  # Keep track of processed image filenames

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_csv', methods=['POST'])
def process_csv():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        csv_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(csv_path)
        
        with open(csv_path, newline='') as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader)  # Skip the header row
            for row in csvreader:
                if row:  # Make sure the row is not empty
                    image_url = row[0]
                    image_name = row[1]
                    process_image_from_url(image_url, image_name)
        
        # Create a zip file of all processed images
        zip_filename = "processed_images.zip"
        zip_path = os.path.join(PROCESSED_FOLDER, zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(PROCESSED_FOLDER):
                for file in files:
                    if file != zip_filename:
                        zipf.write(os.path.join(root, file), file)

        # Clean up processed images directory
        clean_processed_images()

        return redirect(url_for('download_file', filename=zip_filename))

def process_image_from_url(url, name):
    global processed_images
    response = requests.get(url)
    if response.status_code == 200:
        input_image = Image.open(BytesIO(response.content))
        
        # Enhance image quality before background removal
        input_image = enhance_image_quality(input_image)
        
        # Remove background
        output_image = remove(input_image)
        
        # Resize image to 500x500
        output_image = output_image.resize((500, 500), Image.LANCZOS)
        
        # Enhance image quality after resizing
        output_image = enhance_image_quality(output_image)
        
        # Create a white background image
        white_background = Image.new("RGB", output_image.size, (255, 255, 255))
        
        # Paste the image with removed background onto the white background
        white_background.paste(output_image, (0, 0), output_image)
        
        # Save the processed image as JPG
        output_filename = f"{name}.jpg"
        if output_filename not in processed_images:  # Avoid duplicates
            output_path = os.path.join(PROCESSED_FOLDER, output_filename)
            white_background.save(output_path, 'JPEG')
            processed_images.add(output_filename)

def enhance_image_quality(image):
    # Enhance image quality
    enhancer = ImageEnhance.Contrast(image)
    enhanced_image = enhancer.enhance(1.5)  # Increase contrast by 50%
    return enhanced_image

def clean_processed_images():
    for filename in os.listdir(PROCESSED_FOLDER):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            os.remove(os.path.join(PROCESSED_FOLDER, filename))

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(PROCESSED_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
