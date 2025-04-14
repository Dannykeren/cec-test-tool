#!/usr/bin/env python3
"""
CEC Test Tool - Web Server with Integrated GPIO Handling
Serves the web GUI and handles API requests
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
gpio_thread = None
oled_initialized = False

# GPIO Configuration
POWER_ON_PIN = 17   # Physical pin 11
POWER_OFF_PIN = 27  # Physical pin 13
gpio_initialized = False
gpio_running = False

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

def init_gpio():
    """Initialize GPIO directly in server"""
    global gpio_initialized
    
    try:
        # Clean up any existing setup
        try:
            GPIO.cleanup()
        except:
            pass
            
        # Set mode and configure pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        logger.info(f"GPIO initialized directly in server. Pins: ON={POWER_ON_PIN}, OFF={POWER_OFF_PIN}")
        gpio_initialized = True
        return True
    except Exception as e:
        logger.error(f"GPIO initialization failed: {e}")
        gpio_initialized = False
        return False

def gpio_monitoring_thread():
    """Thread function for monitoring GPIO pins"""
    global gpio_running
    
    if not gpio_initialized:
        logger.error("Cannot start GPIO monitoring - GPIO not initialized")
        return
    
    logger.info("Starting GPIO monitoring thread")
    gpio_running = True
    
    # Initialize state tracking
    prev_on = GPIO.input(POWER_ON_PIN)
    prev_off = GPIO.input(POWER_OFF_PIN)
    last_on_time = 0
    last_off_time = 0
    on_presses = 0
    off_presses = 0
    
    try:
        while gpio_running:
            # Read current pin states
            curr_on = GPIO.input(POWER_ON_PIN)
            curr_off = GPIO.input(POWER_OFF_PIN)
            curr_time = time.time()
            
            # Detect ON button press (LOW to HIGH transition)
            if curr_on == 1 and prev_on == 0:
                if curr_time - last_on_time > 0.3:  # 300ms debounce
                    on_presses += 1
                    logger.info(f"ON button pressed #{on_presses}")
                    cec_control.power_on()
                    last_on_time = curr_time
            
            # Detect OFF button press (LOW to HIGH transition)
            if curr_off == 1 and prev_off == 0:
                if curr_time - last_off_time > 0.3:  # 300ms debounce
                    off_presses += 1
                    logger.info(f"OFF button pressed #{off_presses}")
                    cec_control.power_off()
                    last_off_time = curr_time
            
            # Update previous states
            prev_on = curr_on
            prev_off = curr_off
            
            # Sleep briefly
            time.sleep(0.05)
    
    except Exception as e:
        logger.error(f"Error in GPIO monitoring thread: {e}")
    finally:
        logger.info("GPIO monitoring thread stopped")

def start_gpio_thread():
    """Start the GPIO monitoring thread"""
    global gpio_thread
    
    # Initialize GPIO first
    if not gpio_initialized:
        if not init_gpio():
            logger.error("Failed to initialize GPIO, cannot start monitoring thread")
            return False
    
    # Check if thread is already running
    if gpio_thread and gpio_thread.is_alive():
        logger.info("GPIO thread already running")
        return True
    
    # Start thread
    try:
        gpio_thread = threading.Thread(target=gpio_monitoring_thread)
        gpio_thread.daemon = True
        gpio_thread.start()
        
        if gpio_thread.is_alive():
            logger.info("GPIO monitoring thread started successfully")
            return True
        else:
            logger.error("Failed to start GPIO thread")
            return False
    except Exception as e:
        logger.error(f"Error starting GPIO thread: {e}")
        return False

def initialize_hardware():
    """Initialize the hardware components"""
    global oled_initialized
    
    # Initialize OLED display
    try:
        oled_initialized = oled_display.initialize_display()
        if oled_initialized:
            ip_address = get_ip_address()
            oled_display.show_status("Starting...", "CEC Test Tool")
            time.sleep(2)
            oled_display.show_ip_address(f"http://{ip_address}:5000")
        else:
            logger.warning("Failed to initialize OLED display")
    except Exception as e:
        logger.error(f"OLED display error: {e}")
        oled_initialized = False
    
    # Initialize and start GPIO monitoring
    start_gpio_thread()

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
        gpio_running = False
        if oled_initialized:
            oled_display.cleanup()
        try:
            GPIO.cleanup()
        except:
            pass
