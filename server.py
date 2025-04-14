#!/usr/bin/env python3
"""
CEC Test Tool - Web Server with Interrupt Reset Approach
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
reset_thread = None

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

def power_on_callback(channel):
    """Callback for power on button press"""
    logger.info("POWER ON button pressed")
    cec_control.power_on()
    
    # Schedule a reset of the event detection
    schedule_reset()

def power_off_callback(channel):
    """Callback for power off button press"""
    logger.info("POWER OFF button pressed")
    cec_control.power_off()
    
    # Schedule a reset of the event detection
    schedule_reset()

def schedule_reset():
    """Schedule a reset of the event detection"""
    global reset_thread
    
    if reset_thread is None or not reset_thread.is_alive():
        reset_thread = threading.Thread(target=delayed_reset)
        reset_thread.daemon = True
        reset_thread.start()

def delayed_reset():
    """Reset the event detection after a short delay"""
    try:
        # Allow time for the current callback to complete
        time.sleep(0.5)
        
        logger.debug("Performing GPIO event detection reset")
        
        # Remove existing event detection
        GPIO.remove_event_detect(POWER_ON_PIN)
        GPIO.remove_event_detect(POWER_OFF_PIN)
        
        # Brief pause
        time.sleep(0.1)
        
        # Re-add event detection
        GPIO.add_event_detect(POWER_ON_PIN, GPIO.RISING, 
                             callback=power_on_callback, 
                             bouncetime=300)
        
        GPIO.add_event_detect(POWER_OFF_PIN, GPIO.RISING, 
                             callback=power_off_callback, 
                             bouncetime=300)
        
        logger.debug("GPIO event detection reset complete")
    except Exception as e:
        logger.error(f"Error in delayed reset: {e}")

def setup_gpio():
    """Set up GPIO with event detection"""
    try:
        # Clean up any existing setup
        try:
            GPIO.cleanup()
        except:
            pass
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Add event detection
        GPIO.add_event_detect(POWER_ON_PIN, GPIO.RISING, 
                             callback=power_on_callback, 
                             bouncetime=300)
        
        GPIO.add_event_detect(POWER_OFF_PIN, GPIO.RISING, 
                             callback=power_off_callback, 
                             bouncetime=300)
        
        logger.info("GPIO setup with event detection completed")
        return True
    except Exception as e:
        logger.error(f"GPIO setup failed: {e}")
        return False

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
    
    # Setup GPIO
    if not setup_gpio():
        logger.error("Failed to setup GPIO")

def monitor_thread_function():
    """Thread function for monitoring and resetting GPIO if needed"""
    logger.info("Starting GPIO monitoring thread")
    
    last_check_time = time.time()
    
    while running:
        try:
            current_time = time.time()
            
            # Periodically (every 30 seconds) log status and check GPIO
            if current_time - last_check_time > 30:
                on_state = GPIO.input(POWER_ON_PIN)
                off_state = GPIO.input(POWER_OFF_PIN)
                logger.info(f"GPIO Status - ON pin: {on_state}, OFF pin: {off_state}")
                
                last_check_time = current_time
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in monitor thread: {e}")
            time.sleep(5)
            
            # Try to recover
            try:
                setup_gpio()
            except:
                pass

if __name__ == '__main__':
    try:
        # Initialize hardware
        initialize_hardware()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_thread_function)
        monitor_thread.daemon = True
        monitor_thread.start()
        
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
