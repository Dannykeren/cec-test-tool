#!/usr/bin/env python3
"""
CEC Test Tool - Web Server with Ultra-Simple GPIO Handling
"""
import os
import logging
import json
import socket
import threading
import time
import RPi.GPIO as GPIO
from flask import Flask, request, jsonify, send_from_directory
import cec_control
import oled_display

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("server")

# Create Flask app
app = Flask(__name__, static_folder="web_gui", static_url_path='')

# Initialize hardware
oled_initialized = False

# GPIO Configuration
POWER_ON_PIN = 17   # Physical pin 11
POWER_OFF_PIN = 27  # Physical pin 13
running = True

def get_ip_address():
    """Get the IP address of the Raspberry Pi"""
    try:
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
    
    if oled_initialized:
        oled_display.show_power_on()
    
    return jsonify({'status': 'success', 'result': result})

@app.route('/api/power/off', methods=['POST'])
def power_off():
    """API endpoint to power off devices"""
    result = cec_control.power_off()
    
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

def simple_gpio_loop():
    """Ultra-simple GPIO monitoring loop"""
    logger.info("Starting ultra-simple GPIO loop")
    
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Initialize state
        prev_on = 0
        prev_off = 0
        on_count = 0
        off_count = 0
        
        logger.info("GPIO initialized in ultra-simple mode")
        
        # Ultra-simple monitoring loop
        while running:
            # Get current button states
            curr_on = GPIO.input(POWER_ON_PIN)
            curr_off = GPIO.input(POWER_OFF_PIN)
            
            # Check for button presses (LOW to HIGH transitions)
            if curr_on == 1 and prev_on == 0:
                on_count += 1
                logger.info(f"POWER ON button pressed (#{on_count})")
                cec_control.power_on()
            
            if curr_off == 1 and prev_off == 0:
                off_count += 1
                logger.info(f"POWER OFF button pressed (#{off_count})")
                cec_control.power_off()
            
            # Update previous states
            prev_on = curr_on
            prev_off = curr_off
            
            # Brief sleep
            time.sleep(0.05)
            
    except Exception as e:
        logger.error(f"Error in GPIO loop: {e}")
    finally:
        logger.info("GPIO loop ended")
        try:
            GPIO.cleanup()
        except:
            pass

def initialize_hardware():
    """Initialize hardware components"""
    global oled_initialized
    
    # Initialize OLED display
    try:
        oled_initialized = oled_display.initialize_display()
        if oled_initialized:
            ip_address = get_ip_address()
            oled_display.show_status("Starting...", "CEC Test Tool")
            time.sleep(1)
            oled_display.show_ip_address(f"http://{ip_address}:5000")
        else:
            logger.warning("Failed to initialize OLED display")
    except Exception as e:
        logger.error(f"OLED display error: {e}")
        oled_initialized = False
    
    # Start GPIO thread
    gpio_thread = threading.Thread(target=simple_gpio_loop)
    gpio_thread.daemon = True
    gpio_thread.start()
    if gpio_thread.is_alive():
        logger.info("GPIO monitoring thread started")
    else:
        logger.error("Failed to start GPIO thread")

if __name__ == '__main__':
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
        running = False
        if oled_initialized:
            oled_display.cleanup()
        try:
            GPIO.cleanup()
        except:
            pass
