#!/usr/bin/env python3
"""
CEC Test Tool - Web Server
Modified to work with standalone GPIO handler
"""
import os
import logging
import json
import socket
import threading
import time
import subprocess
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
gpio_handler_process = None

# Command file paths
COMMAND_DIR = "/tmp/cec_commands"
ON_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_on_trigger")
OFF_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_off_trigger")

# Last processed command times
last_processed = {
    'on': 0,
    'off': 0
}

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

def check_command_files():
    """Check for command trigger files and process them"""
    global last_processed
    
    # Check ON command file
    if os.path.exists(ON_COMMAND_FILE):
        try:
            # Read timestamp from file
            with open(ON_COMMAND_FILE, 'r') as f:
                timestamp = float(f.read().strip())
            
            # Check if this is a new command
            if timestamp > last_processed['on']:
                logger.info(f"Processing power ON command from GPIO handler")
                cec_control.power_on()
                last_processed['on'] = timestamp
                
                # Show on OLED if available
                if oled_initialized:
                    oled_display.show_power_on()
            
            # Remove the trigger file
            os.remove(ON_COMMAND_FILE)
            
        except Exception as e:
            logger.error(f"Error processing ON command file: {e}")
    
    # Check OFF command file
    if os.path.exists(OFF_COMMAND_FILE):
        try:
            # Read timestamp from file
            with open(OFF_COMMAND_FILE, 'r') as f:
                timestamp = float(f.read().strip())
            
            # Check if this is a new command
            if timestamp > last_processed['off']:
                logger.info(f"Processing power OFF command from GPIO handler")
                cec_control.power_off()
                last_processed['off'] = timestamp
                
                # Show on OLED if available
                if oled_initialized:
                    oled_display.show_power_off()
            
            # Remove the trigger file
            os.remove(OFF_COMMAND_FILE)
            
        except Exception as e:
            logger.error(f"Error processing OFF command file: {e}")

def command_monitor_thread():
    """Thread to monitor for command files from the GPIO handler"""
    logger.info("Starting command monitor thread")
    
    # Create command directory if it doesn't exist
    try:
        os.makedirs(COMMAND_DIR, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create command directory: {e}")
    
    # Main monitoring loop
    while True:
        try:
            # Check for command files
            check_command_files()
            
            # Sleep briefly
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error in command monitor thread: {e}")
            time.sleep(1)

def start_gpio_handler():
    """Start the GPIO handler as a separate Python process"""
    global gpio_handler_process
    
    try:
        # Check if script exists
        handler_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpio_handler.py")
        if not os.path.exists(handler_script):
            logger.error(f"GPIO handler script not found at {handler_script}")
            return False
        
        # Make sure it's executable
        os.chmod(handler_script, 0o755)
        
        # Start the process
        logger.info(f"Starting GPIO handler process: {handler_script}")
        gpio_handler_process = subprocess.Popen(["python3", handler_script], 
                                               stdout=subprocess.PIPE, 
                                               stderr=subprocess.PIPE)
        
        # Check if process started successfully
        if gpio_handler_process.poll() is None:
            logger.info("GPIO handler process started successfully")
            return True
        else:
            logger.error("GPIO handler process failed to start")
            return False
            
    except Exception as e:
        logger.error(f"Error starting GPIO handler: {e}")
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
    
    # Start GPIO handler as separate process
    if not start_gpio_handler():
        logger.warning("Failed to start GPIO handler process, buttons may not work")
    
    # Start command monitor thread
    monitor_thread = threading.Thread(target=command_monitor_thread)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    if monitor_thread.is_alive():
        logger.info("Command monitor thread started successfully")
    else:
        logger.error("Failed to start command monitor thread")

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
        if oled_initialized:
            oled_display.cleanup()
        
        # Terminate GPIO handler process if running
        if gpio_handler_process and gpio_handler_process.poll() is None:
            try:
                gpio_handler_process.terminate()
                logger.info("GPIO handler process terminated")
            except:
                pass
