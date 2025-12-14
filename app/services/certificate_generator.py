"""
Certificate Generator Service
Generates certificates by overlaying text on a PNG template.
"""

import os
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.utils import ImageReader
from datetime import datetime


class CertificateGenerator:
    """Generate certificates with custom PNG templates."""
    
    # Default template path
    TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'certificates')
    DEFAULT_TEMPLATE = 'template.png'
    
    # Font settings - use default fonts that are available on most systems
    FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'fonts')
    
    # High resolution for quality
    BASE_WIDTH = 3840  # 4K width
    BASE_HEIGHT = 2160  # 4K height
    
    # Color scheme - consistent primary color
    PRIMARY_COLOR = "#e94560"
    SECONDARY_COLOR = "#888888"
    LABEL_COLOR = "#666666"
    
    @classmethod
    def get_font(cls, size, bold=False):
        """Get a font, falling back to default if custom fonts not available."""
        try:
            # Try to load a custom font
            font_name = 'Poppins-Bold.ttf' if bold else 'Poppins-Regular.ttf'
            font_path = os.path.join(cls.FONTS_DIR, font_name)
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
            
            # Fallback to system fonts
            system_fonts = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf' if bold else '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
                'arial.ttf',
                'Arial.ttf'
            ]
            
            for font in system_fonts:
                try:
                    return ImageFont.truetype(font, size)
                except:
                    continue
            
            # Ultimate fallback
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()
    
    @classmethod
    def generate_certificate_image(cls, student_name: str, course_title: str, 
                                    instructor_name: str, certificate_code: str,
                                    attendance_count: int, total_classes: int,
                                    attendance_percentage: float, issued_date: datetime,
                                    template_name: str = None) -> io.BytesIO:
        """
        Generate a certificate image with text overlay.
        
        Returns a BytesIO object containing the PNG image.
        """
        template_path = os.path.join(cls.TEMPLATE_DIR, template_name or cls.DEFAULT_TEMPLATE)
        
        # Check if template exists, if not create a default one
        if not os.path.exists(template_path):
            img = cls._create_default_template()
        else:
            img = Image.open(template_path).convert('RGBA')
            # Scale up template if needed for quality
            if img.width < cls.BASE_WIDTH:
                scale = cls.BASE_WIDTH / img.width
                new_height = int(img.height * scale)
                img = img.resize((cls.BASE_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Font sizes relative to image height for consistency
        title_size = int(height * 0.04)
        subtitle_size = int(height * 0.025)
        name_size = int(height * 0.07)
        course_size = int(height * 0.05)
        attendance_size = int(height * 0.022)
        info_size = int(height * 0.024)
        label_size = int(height * 0.018)
        
        # Certificate title
        title_font = cls.get_font(title_size, bold=True)
        cls._draw_centered_text(draw, "CERTIFICATE OF COMPLETION", 
                               width // 2, int(height * 0.20), title_font, cls.PRIMARY_COLOR)
        
        # "This is to certify that"
        subtitle_font = cls.get_font(subtitle_size)
        cls._draw_centered_text(draw, "This is to certify that",
                               width // 2, int(height * 0.30), subtitle_font, cls.SECONDARY_COLOR)
        
        # Student Name (large, prominent) - SAME COLOR AS COURSE TITLE
        name_font = cls.get_font(name_size, bold=True)
        cls._draw_centered_text(draw, student_name,
                               width // 2, int(height * 0.39), name_font, cls.PRIMARY_COLOR)
        
        # "has successfully completed the course"
        cls._draw_centered_text(draw, "has successfully completed the course",
                               width // 2, int(height * 0.48), subtitle_font, cls.SECONDARY_COLOR)
        
        # Course Title - PRIMARY COLOR
        course_font = cls.get_font(course_size, bold=True)
        cls._draw_centered_text(draw, course_title,
                               width // 2, int(height * 0.56), course_font, cls.PRIMARY_COLOR)
        
        # Attendance info
        attendance_font = cls.get_font(attendance_size)
        attendance_text = f"Attendance: {attendance_count}/{total_classes} classes ({attendance_percentage}%)"
        cls._draw_centered_text(draw, attendance_text,
                               width // 2, int(height * 0.65), attendance_font, cls.SECONDARY_COLOR)
        
        # Bottom section - Instructor, Date, Certificate ID
        info_font = cls.get_font(info_size, bold=True)
        label_font = cls.get_font(label_size)
        bottom_y = int(height * 0.78)
        label_offset = int(height * 0.04)
        
        # Instructor name (left side) - PRIMARY COLOR
        instructor_x = int(width * 0.18)
        cls._draw_centered_text(draw, instructor_name, instructor_x, bottom_y, info_font, cls.PRIMARY_COLOR)
        # Draw underline
        instructor_bbox = draw.textbbox((0, 0), instructor_name, font=info_font)
        line_width = instructor_bbox[2] - instructor_bbox[0]
        draw.line([(instructor_x - line_width//2, bottom_y + int(height * 0.02)), 
                   (instructor_x + line_width//2, bottom_y + int(height * 0.02))],
                  fill=cls.LABEL_COLOR, width=2)
        cls._draw_centered_text(draw, "Course Instructor", instructor_x, bottom_y + label_offset, label_font, cls.LABEL_COLOR)
        
        # Issue date (center) - PRIMARY COLOR
        date_str = issued_date.strftime("%B %d, %Y")
        date_x = width // 2
        cls._draw_centered_text(draw, date_str, date_x, bottom_y, info_font, cls.PRIMARY_COLOR)
        # Draw underline
        date_bbox = draw.textbbox((0, 0), date_str, font=info_font)
        line_width = date_bbox[2] - date_bbox[0]
        draw.line([(date_x - line_width//2, bottom_y + int(height * 0.02)), 
                   (date_x + line_width//2, bottom_y + int(height * 0.02))],
                  fill=cls.LABEL_COLOR, width=2)
        cls._draw_centered_text(draw, "Date Issued", date_x, bottom_y + label_offset, label_font, cls.LABEL_COLOR)
        
        # Certificate code (right side) - PRIMARY COLOR
        code_x = int(width * 0.82)
        cls._draw_centered_text(draw, certificate_code, code_x, bottom_y, info_font, cls.PRIMARY_COLOR)
        # Draw underline
        code_bbox = draw.textbbox((0, 0), certificate_code, font=info_font)
        line_width = code_bbox[2] - code_bbox[0]
        draw.line([(code_x - line_width//2, bottom_y + int(height * 0.02)), 
                   (code_x + line_width//2, bottom_y + int(height * 0.02))],
                  fill=cls.LABEL_COLOR, width=2)
        cls._draw_centered_text(draw, "Certificate ID", code_x, bottom_y + label_offset, label_font, cls.LABEL_COLOR)
        
        # Enhance image quality
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        
        # Save to BytesIO with high quality
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG', optimize=False)
        img_buffer.seek(0)
        
        return img_buffer
    
    @classmethod
    def generate_certificate_pdf(cls, student_name: str, course_title: str,
                                  instructor_name: str, certificate_code: str,
                                  attendance_count: int, total_classes: int,
                                  attendance_percentage: float, issued_date: datetime,
                                  template_name: str = None) -> io.BytesIO:
        """
        Generate a certificate PDF.
        
        Returns a BytesIO object containing the PDF.
        """
        # First generate the image
        img_buffer = cls.generate_certificate_image(
            student_name, course_title, instructor_name, certificate_code,
            attendance_count, total_classes, attendance_percentage, issued_date,
            template_name
        )
        
        # Create PDF
        pdf_buffer = io.BytesIO()
        
        # Get image dimensions for PDF sizing
        img = Image.open(img_buffer)
        img_width, img_height = img.size
        
        # Calculate PDF page size to match image aspect ratio (A4 landscape base)
        aspect_ratio = img_width / img_height
        pdf_height = A4[1]  # A4 height in points
        pdf_width = pdf_height * aspect_ratio
        
        c = canvas.Canvas(pdf_buffer, pagesize=(pdf_width, pdf_height))
        
        # Reset image buffer position
        img_buffer.seek(0)
        
        # Draw image on PDF with high quality
        c.drawImage(ImageReader(img_buffer), 0, 0, width=pdf_width, height=pdf_height)
        
        c.save()
        pdf_buffer.seek(0)
        
        return pdf_buffer
    
    @classmethod
    def _draw_centered_text(cls, draw, text, x, y, font, color):
        """Draw text centered at the given coordinates with anti-aliasing."""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text((x - text_width // 2, y - text_height // 2), text, font=font, fill=color)
    
    @classmethod
    def _create_default_template(cls) -> Image.Image:
        """Create a default certificate template if none exists."""
        # Create a high-resolution landscape certificate (4K)
        width, height = cls.BASE_WIDTH, cls.BASE_HEIGHT
        
        # Create gradient background
        img = Image.new('RGBA', (width, height), (26, 26, 46, 255))
        draw = ImageDraw.Draw(img)
        
        # Draw smooth gradient effect
        for i in range(height):
            progress = i / height
            r = int(20 + (12 - 20) * progress)
            g = int(20 + (28 - 20) * progress)
            b = int(40 + (55 - 40) * progress)
            draw.line([(0, i), (width, i)], fill=(r, g, b, 255))
        
        # Draw outer border
        border_color = (233, 69, 96, 255)  # #e94560
        border_width = 16
        draw.rectangle([border_width//2, border_width//2, 
                       width - border_width//2, height - border_width//2],
                       outline=border_color, width=border_width)
        
        # Draw inner decorative border
        inner_margin = 60
        draw.rectangle([inner_margin, inner_margin,
                       width - inner_margin, height - inner_margin],
                       outline=(233, 69, 96, 120), width=3)
        
        # Draw decorative corners with larger size
        corner_size = 120
        corner_color = (233, 69, 96, 200)
        corner_width = 5
        
        # Top-left corner
        draw.line([(inner_margin, inner_margin + corner_size), 
                   (inner_margin, inner_margin), 
                   (inner_margin + corner_size, inner_margin)], 
                  fill=corner_color, width=corner_width)
        
        # Top-right corner
        draw.line([(width - inner_margin - corner_size, inner_margin),
                   (width - inner_margin, inner_margin),
                   (width - inner_margin, inner_margin + corner_size)],
                  fill=corner_color, width=corner_width)
        
        # Bottom-left corner
        draw.line([(inner_margin, height - inner_margin - corner_size),
                   (inner_margin, height - inner_margin),
                   (inner_margin + corner_size, height - inner_margin)],
                  fill=corner_color, width=corner_width)
        
        # Bottom-right corner
        draw.line([(width - inner_margin - corner_size, height - inner_margin),
                   (width - inner_margin, height - inner_margin),
                   (width - inner_margin, height - inner_margin - corner_size)],
                  fill=corner_color, width=corner_width)
        
        # Draw Guruji logo/text at top
        logo_font = cls.get_font(96, bold=True)
        cls._draw_centered_text(draw, "🎓 Guruji", width // 2, 140, logo_font, cls.PRIMARY_COLOR)
        
        # Draw decorative line under logo
        line_y = 220
        line_width = 400
        draw.line([(width//2 - line_width, line_y), (width//2 + line_width, line_y)],
                  fill=(233, 69, 96, 150), width=4)
        
        # Add subtle decorative elements
        # Top decorative circles
        for offset in [-300, 300]:
            draw.ellipse([width//2 + offset - 8, line_y - 8, width//2 + offset + 8, line_y + 8],
                        fill=(233, 69, 96, 150))
        
        return img
