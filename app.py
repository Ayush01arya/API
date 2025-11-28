from flask import Flask, request, send_file, jsonify
import io
import os
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

app = Flask(__name__)

# --- CONFIGURATION (Vercel Compatible Paths) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'IBMPlexSansDevanagari-Regular.ttf')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'static', 'template.png')
FONT_NAME = "IBMPlexSansDevanagari"

def register_custom_fonts():
    """Registers the font if found."""
    if os.path.exists(FONT_PATH):
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
            return True
        except Exception as e:
            print(f"Font Error: {e}")
            return False
    return False

def generate_pdf_in_memory(data):
    """Generates PDF and returns the binary buffer."""
    
    # 1. Create In-Memory Buffer
    packet = io.BytesIO()
    
    # 2. Setup Canvas
    c = canvas.Canvas(packet, pagesize=A4)
    page_width, page_height = A4
    
    # Register Font
    has_custom_font = register_custom_fonts()
    main_font = FONT_NAME if has_custom_font else "Helvetica"

    # 3. Draw Template
    if os.path.exists(TEMPLATE_PATH):
        try:
            c.drawImage(TEMPLATE_PATH, 0, 0, width=page_width, height=page_height)
        except Exception as e:
            print(f"Template Load Error: {e}")
    
    # ---------------------------------------------------------
    # PHOTO SECTION (Rounded, No Border, Fixed Clipping)
    # ---------------------------------------------------------
    photo_url = data.get('candidate_photo')
    # Use your exact coordinates
    img_x = 465
    img_w = 84
    img_h = 91
    img_y = page_height - 108 - img_h
    border_radius = 5

    if photo_url:
        try:
            # We use ImageReader to handle URL downloads automatically
            img = ImageReader(photo_url)
            
            # --- CLIPPING MAGIC ---
            c.saveState()
            
            # 1. Create Path
            path = c.beginPath()
            path.roundRect(img_x, img_y, img_w, img_h, border_radius)
            
            # 2. Clip to Path
            c.clipPath(path, stroke=0)
            
            # 3. Draw Image
            c.drawImage(img, img_x, img_y, width=img_w, height=img_h, mask='auto')
            
            c.restoreState()
            # ----------------------
        except Exception as e:
            print(f"Photo Error: {e}")

    # ---------------------------------------------------------
    # DETAILS SECTION (Coordinates from your perfect code)
    # ---------------------------------------------------------
    text_x = 50
    name_y = 700
    role_y = 683
    date_y = 665
    id_y   = 645

    c.setFont(main_font, 14)
    c.setFillColor(colors.white)
    # Use .get() to avoid errors if key is missing
    c.drawString(text_x, name_y, str(data.get('name', '')))

    c.setFont(main_font, 12)
    c.drawString(text_x, role_y, str(data.get('role', '')))
    c.drawString(text_x, date_y, str(data.get('date', '')))
    c.drawString(text_x, id_y, str(data.get('interview_id', '')))

    # ---------------------------------------------------------
    # AI OVERVIEW SECTION (Full Width, No Charts)
    # ---------------------------------------------------------
    ai_overview = data.get('ai_overview', '')
    
    box_x = 56
    input_y_from_top = 281
    box_height = 111
    # Reverting to full width since charts are gone
    box_width = 502 
    
    pdf_box_top_y = page_height - input_y_from_top
    
    styles = getSampleStyleSheet()
    ai_style = ParagraphStyle(
        'AI_Box',
        parent=styles['Normal'],
        fontName=main_font,
        fontSize=11,
        leading=15,
        textColor=colors.white,
        alignment=4, # Justified
        wordWrap='CJK'
    )

    formatted_text = ai_overview.replace('\n', '<br/>')
    p = Paragraph(formatted_text, ai_style)
    
    # Calculate available space
    safe_width = min(box_width, page_width - box_x - 10)
    w, h = p.wrap(safe_width, box_height)
    
    # Draw
    p.drawOn(c, box_x, pdf_box_top_y - h)

    # 4. Finalize
    c.save()
    packet.seek(0)
    return packet

# --- API ROUTE ---
@app.route('/generate-pdf', methods=['POST'])
def handle_pdf_generation():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Create PDF
        pdf_buffer = generate_pdf_in_memory(data)
        
        # Filename
        filename = f"{data.get('interview_id', 'report')}.pdf"

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Local Testing
if __name__ == '__main__':
    app.run(debug=True, port=5000)
