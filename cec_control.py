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

def execute_cec_command(command):
    """Execute a CEC command and return the output"""
    try:
        result = subprocess.run(['cec-client', '-s', '-d', '1'],
                               input=command.encode(),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               timeout=5)
        return result.stdout.decode()
    except subprocess.TimeoutExpired:
        logger.error("CEC command timed out")
        return "Command timed out"
    except Exception as e:
        logger.error(f"Error executing CEC command: {e}")
        return f"Error: {str(e)}"

def is_rate_limited():
    """Check if we should rate limit commands to prevent looping"""
    global last_command_time
    current_time = time.time()
    if current_time - last_command_time < COMMAND_COOLDOWN:
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
        logger.warning("Command rate limited to prevent looping")
        return "Rate limited. Please wait before sending another command."
    
    logger.info("Sending power ON command")
    return execute_cec_command("on 0")

def power_off():
    """Send power off command to all devices"""
    if is_rate_limited():
        logger.warning("Command rate limited to prevent looping")
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
        logger.warning("Command rate limited to prevent looping")
        return "Rate limited. Please wait before sending another command."
    
    logger.info(f"Sending custom command: {command}")
    return execute_cec_command(command)

# Simple self-test when run directly
if __name__ == "__main__":
    print("CEC Controller Test")
    print("-----------------")
    print("Scanning for devices:")
    print(scan_devices())
    print("\nThe CEC controller is ready to use.")
