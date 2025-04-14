#!/usr/bin/env python3
"""
CEC Test Tool - CEC Controller Module
Handles CEC commands and prevents command looping
"""
import subprocess
import time
import logging
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cec_control.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cec_control")

# Anti-looping protection
COMMAND_COOLDOWN = 2.0  # seconds
last_command_time = 0

# Global variable to store the cec-client process
cec_process = None

def initialize_cec():
    """Initialize a persistent CEC client connection"""
    global cec_process
    try:
        if cec_process is None or cec_process.poll() is not None:
            logger.info("Starting persistent CEC client connection")
            cec_process = subprocess.Popen(['cec-client', '-d', '1'],
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         universal_newlines=True)
            time.sleep(2)  # Give it time to initialize
        return True
    except Exception as e:
        logger.error(f"Failed to initialize CEC client: {e}")
        return False

def execute_cec_command(command):
    """Execute a CEC command using the persistent connection"""
    global cec_process
    try:
        if not initialize_cec():
            return "Failed to initialize CEC client"
            
        logger.debug(f"Sending CEC command: {command}")
        cec_process.stdin.write(command + "\n")
        cec_process.stdin.flush()
        
        # Wait for response with a reasonable timeout
        response = ""
        start_time = time.time()
        while time.time() - start_time < 8:  # 8-second timeout
            line = cec_process.stdout.readline()
            if line:
                response += line
            else:
                time.sleep(0.1)
                
            # Basic check if we've received a complete response
            if "CEC bus information" in response or "TRAFFIC:" in response:
                break
        
        logger.debug(f"CEC response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error executing CEC command: {e}")
        # Try to reinitialize the connection on error
        initialize_cec()
        return f"Error: {str(e)}"

def is_rate_limited():
    """Check if we should rate limit commands to prevent looping"""
    global last_command_time
    current_time = time.time()
    if current_time - last_command_time < COMMAND_COOLDOWN:
        logger.warning("Command rate limited to prevent looping")
        return True
    last_command_time = current_time
    return False

def scan_devices():
    """Scan for CEC devices"""
    logger.info("Scanning for CEC devices")
    return execute_cec_command("scan")

def power_on():
    """Send power on command to all devices"""
    if is_rate_limited():
        return "Rate limited. Please wait before sending another command."
    
    logger.info("Sending power ON command")
    return execute_cec_command("on 0")

def power_off():
    """Send power off command to all devices"""
    if is_rate_limited():
        return "Rate limited. Please wait before sending another command."
    
    logger.info("Sending power OFF command")
    return execute_cec_command("standby 0")

def get_power_status():
    """Get the power status of connected devices"""
    logger.info("Getting power status")
    return execute_cec_command("pow")

def send_custom_command(command):
    """Send a custom CEC command"""
    if is_rate_limited():
        return "Rate limited. Please wait before sending another command."
    
    logger.info(f"Sending custom command: {command}")
    return execute_cec_command(command)

# Initialize CEC connection when module is loaded
initialize_cec()

# Simple self-test when run directly
if __name__ == "__main__":
    print("CEC Controller Test")
    print("-----------------")
    print("Scanning for devices:")
    print(scan_devices())
    print("\nThe CEC controller is ready to use.")
