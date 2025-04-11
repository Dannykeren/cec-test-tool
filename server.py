#!/usr/bin/env python3
"""
CEC Test Tool - Web Server
Serves the web GUI and handles API requests
"""
import os
import logging
import json
import socket
import threading
from flask import Flask, request, jsonify, send_from_directory
import cec_control
import gpio_handler
import oled_display

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("server")

# Create Flask app
app = Flask(__name__, static_folder="web_gui")

# Initialize hardware
gpio_thread = None
oled_initialized = False

def get_ip_address():
    """Get the IP address of the Raspberry Pi"""
    try:
        # Create a socket connection to get the IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        logger.error(f"Error getting IP address: {e}")
        return "127.0.0.1"  # Fallback to localhost

@app.route('/')
def index():
    """Serve the main web interface"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/scan', methods=['GET'])
def scan_devices():
    """API endpoint to scan for CEC devices"""
    result = cec_control.scan_devices()
    return jsonify({'status': 'success', 'result': result})

@app.route('/api/power/on', methods=['POST'])
def power_on():
    """API endpoint to power on devices"""
    result = cec_control.power_on()
    
    # Update OLED display
    if oled_initialized:
        oled_display.show_power_on()
    
    return jsonify({'status': 'success', 'result': result})

@app.route('/api/power/off', methods=['POST'])
def power_off():
    """API endpoint to power off devices"""
    result = cec_control.power_off()
    
    # Update OLED display
    if oled_initialized:
        oled_display.show_power_off()
    
    return jsonify({'status': 'success', 'result': result})

@app.route('/api/status', methods=['GET'])
def get_status():
    """API endpoint to get the power status"""
    result = cec_control.get_power_status()
    return jsonify({'status': 'success', 'result': result})

@app.route('/api/command', methods=['POST'])
def custom_command():
    """API endpoint to send a custom CEC command"""
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({'status': 'error', 'message': 'Command is required'}), 400
    
    result = cec_control.send_custom_command(data['command'])
    return jsonify({'status': 'success', 'result': result})

def start_gpio_thread():
    """Start the GPIO handler in a separate thread"""
    global gpio_thread
    gpio_thread = threading.Thread(target=gpio_handler.start_gpio_handler)
    gpio_thread.daemon = True  # Thread will exit when the main program exits
    gpio_thread.start()

def initialize_hardware():
    """Initialize the hardware components"""
    global oled_initialized
    
    # Initialize OLED display
    oled_initialized = oled_display.initialize_display()
    if oled_initialized:
        ip_address = get_ip_address()
        oled_display.show_status("Starting...", "CEC Test Tool")
        time.sleep(2)
        oled_display.show_ip_address(f"http://{ip_address}:5000")
    
    # Start GPIO handler
    start_gpio_thread()

if __name__ == '__main__':
    import time
    try:
        # Initialize hardware
        initialize_hardware()
        
        # Start the web server
        ip_address = get_ip_address()
        logger.info(f"Starting web server on http://{ip_address}:5000")
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        # Clean up resources
        if oled_initialized:
            oled_display.cleanup()
