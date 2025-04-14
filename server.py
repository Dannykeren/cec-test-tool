#!/usr/bin/env python3
"""
CEC Test Tool - Web Server with Direct GPIO Monitoring
Simplest possible implementation
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

def direct_gpio_monitor():
    """Direct GPIO monitoring thread without event detection"""
    logger.info("Starting direct GPIO monitoring thread")
    
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        try:
            # First clean up any existing configuration
            GPIO.cleanup(POWER_ON_PIN)
            GPIO.cleanup(POWER_OFF_PIN)
        except:
            pass
        
        # Setup input pins
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        logger.info("GPIO pins configured successfully")
        
        # Initialize variables for state tracking
        last_on_state = GPIO.input(POWER_ON_PIN)
        last_off_state = GPIO.input(POWER_OFF_PIN)
        last_press_time = 0
        on_count = 0
        off_count = 0
        
        # Main monitoring loop
        while running:
            try:
                # Read current pin states
                curr_on_state = GPIO.input(POWER_ON_PIN)
                curr_off_state = GPIO.input(POWER_OFF_PIN)
                curr_time = time.time()
                
                # Check for pin state changes (LOW to HIGH = button press)
                
                # ON button
                if curr_on_state == 1 and last_on_state == 0:
                    # Simple debounce - at least 300ms between presses
                    if curr_time - last_press_time > 0.3:
                        on_count += 1
                        logger.info(f"ON button pressed #{on_count}")
                        
                        # Send CEC command
                        cec_control.power_on()
                        
                        # Update last press time
                        last_press_time = curr_time
                
                # OFF button
                if curr_off_state == 1 and last_off_state == 0:
                    # Simple debounce - at least 300ms between presses
                    if curr_time - last_press_time > 0.3:
                        off_count += 1
                        logger.info(f"OFF button pressed #{off_count}")
                        
                        # Send CEC command
                        cec_control.power_off()
                        
                        # Update last press time
                        last_press_time = curr_time
                
                # Update last states
                last_on_state = curr_on_state
                last_off_state = curr_off_state
                
                # Brief sleep to reduce CPU usage
                time.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Error in GPIO monitoring loop: {e}")
                time.sleep(0.5)
                
                # Try to recover
                try:
                    # Re-configure GPIO pins
                    GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    
                    # Reset state tracking
                    last_on_state = GPIO.input(POWER_ON_PIN)
                    last_off_state = GPIO.input(POWER_OFF_PIN)
                    
                    logger.info("Recovered from GPIO monitoring error")
                except:
                    pass
    
    except Exception as e:
        logger.error(f"Critical error in GPIO monitoring thread: {e}")
    finally:
        logger.info("GPIO monitoring thread stopped")
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
    
    # Start GPIO monitoring thread
    gpio_thread = threading.Thread(target=direct_gpio_monitor)
    gpio_thread.daemon = True
    gpio_thread.start()
    
    if gpio_thread.is_alive():
        logger.info("GPIO monitoring thread started successfully")
    else:
        logger.error("Failed to start GPIO monitoring thread")

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
