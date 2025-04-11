#!/usr/bin/env python3
"""
CEC Test Tool - OLED Display Controller
Handles the small OLED display connected to the Raspberry Pi
"""
import time
import logging
import threading
import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("oled_display.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("oled_display")

# Configuration for the OLED display
# Most common OLED displays are 128x64 or 128x32 pixels
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
I2C_ADDRESS = 0x3C  # The most common address, might need to be adjusted

# Global variables
display = None
draw = None
image = None
font = None
font_large = None
display_lock = threading.Lock()

def initialize_display():
    """Initialize the OLED display"""
    global display, draw, image, font, font_large
    
    try:
        # Create the I2C interface
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # Create the SSD1306 OLED class
        display = adafruit_ssd1306.SSD1306_I2C(
            DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c, addr=I2C_ADDRESS)
        
        # Clear display
        display.fill(0)
        display.show()
        
        # Create blank image for drawing
        image = Image.new("1", (display.width, display.height))
        draw = ImageDraw.Draw(image)
        
        # Load a font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except OSError:
            # If the above font is not available, use the default
            font = ImageFont.load_default()
            font_large = ImageFont.load_default()
        
        logger.info("OLED display initialized")
        return True
    
    except Exception as e:
        logger.error(f"Failed to initialize OLED display: {e}")
        return False

def clear_display():
    """Clear the display"""
    with display_lock:
        if display is None:
            return
        
        draw.rectangle((0, 0, display.width, display.height), outline=0, fill=0)
        update_display()

def show_text(text, x=0, y=0, large_font=False):
    """Show text on the display at the specified position"""
    with display_lock:
        if display is None:
            return
        
        selected_font = font_large if large_font else font
        draw.text((x, y), text, font=selected_font, fill=255)
        update_display()

def show_status(title, status):
    """Show a status screen with title and status"""
    with display_lock:
        if display is None:
            return
        
        clear_display()
        draw.text((0, 0), "CEC Test Tool", font=font_large, fill=255)
        draw.line((0, 18, display.width, 18), fill=255)
        draw.text((0, 22), title, font=font, fill=255)
        draw.text((0, 36), status, font=font_large, fill=255)
        update_display()

def update_display():
    """Update the physical display with the current image"""
    if display is None:
        return
    
    display.image(image)
    display.show()

def show_power_on():
    """Show that power on was activated"""
    show_status("Command sent:", "POWER ON")

def show_power_off():
    """Show that power off was activated"""
    show_status("Command sent:", "POWER OFF")

def show_ip_address(ip_address):
    """Show the IP address of the Raspberry Pi"""
    show_status("Web Interface:", ip_address)

def cleanup():
    """Clean up display resources"""
    with display_lock:
        if display is None:
            return
        
        clear_display()
        logger.info("OLED display resources cleaned up")

# Test the display when run directly
if __name__ == "__main__":
    if initialize_display():
        try:
            show_status("OLED Test", "Working!")
            time.sleep(2)
            show_power_on()
            time.sleep(2)
            show_power_off()
            time.sleep(2)
            show_ip_address("192.168.1.100")
            time.sleep(5)
        finally:
            cleanup()
