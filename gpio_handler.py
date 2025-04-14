#!/usr/bin/env python3
"""
Standalone GPIO Handler for CEC Test Tool
Using event-based detection instead of polling
"""
import RPi.GPIO as GPIO
import time
import logging
import os
import json
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Log to console only to avoid permission issues
    ]
)
logger = logging.getLogger("gpio_handler")

# GPIO Pins
POWER_ON_PIN = 17   # Physical pin 11
POWER_OFF_PIN = 27  # Physical pin 13

# Command file paths
COMMAND_DIR = "/tmp/cec_commands"
ON_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_on_trigger")
OFF_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_off_trigger")

def on_button_callback(channel):
    """Callback for ON button press"""
    logger.info(f"ON button pressed (pin {channel})")
    trigger_power_on()

def off_button_callback(channel):
    """Callback for OFF button press"""
    logger.info(f"OFF button pressed (pin {channel})")
    trigger_power_off()

def setup_gpio():
    """Set up GPIO pins with event detection"""
    try:
        # Clean up any existing setup
        try:
            GPIO.cleanup()
        except:
            pass
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Configure pins with pull-down resistors
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Remove any existing event detection
        try:
            GPIO.remove_event_detect(POWER_ON_PIN)
            GPIO.remove_event_detect(POWER_OFF_PIN)
        except:
            pass
        
        # Add event detection with very long bouncetime
        GPIO.add_event_detect(POWER_ON_PIN, GPIO.RISING, 
                             callback=on_button_callback, bouncetime=1000)
        GPIO.add_event_detect(POWER_OFF_PIN, GPIO.RISING,
                             callback=off_button_callback, bouncetime=1000)
        
        logger.info(f"GPIO pins configured with event detection")
        return True
    except Exception as e:
        logger.error(f"GPIO setup failed: {e}")
        return False

def setup_command_dir():
    """Set up command directory for inter-process communication"""
    try:
        # Create command directory if it doesn't exist
        os.makedirs(COMMAND_DIR, exist_ok=True)
        
        # Clear any existing command files
        if os.path.exists(ON_COMMAND_FILE):
            os.remove(ON_COMMAND_FILE)
        if os.path.exists(OFF_COMMAND_FILE):
            os.remove(OFF_COMMAND_FILE)
        
        logger.info(f"Command directory setup at {COMMAND_DIR}")
        return True
    except Exception as e:
        logger.error(f"Command directory setup failed: {e}")
        return False

def trigger_power_on():
    """Create a trigger file for power on"""
    try:
        # Write timestamp to trigger file
        with open(ON_COMMAND_FILE, 'w') as f:
            f.write(str(time.time()))
        logger.info("Created power ON trigger file")
        
        # Also execute the cec-client command directly as a backup
        try:
            subprocess.run(['cec-client', '-s', '-d', '1', '-o', 'CEC_TEST', '-c', 'on 0'], 
                          timeout=3, 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Error executing cec-client for ON: {e}")
            
    except Exception as e:
        logger.error(f"Failed to create power ON trigger: {e}")

def trigger_power_off():
    """Create a trigger file for power off"""
    try:
        # Write timestamp to trigger file
        with open(OFF_COMMAND_FILE, 'w') as f:
            f.write(str(time.time()))
        logger.info("Created power OFF trigger file")
        
        # Also execute the cec-client command directly as a backup
        try:
            subprocess.run(['cec-client', '-s', '-d', '1', '-o', 'CEC_TEST', '-c', 'standby 0'], 
                          timeout=3, 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Error executing cec-client for OFF: {e}")
            
    except Exception as e:
        logger.error(f"Failed to create power OFF trigger: {e}")

def start_gpio_handler():
    """Main entry point for GPIO handler"""
    logger.info("Starting standalone GPIO handler")
    
    # Setup
    if not setup_gpio():
        logger.error("Failed to set up GPIO pins")
        return
    
    if not setup_command_dir():
        logger.error("Failed to set up command directory")
        return
    
    try:
        # Since we're using event detection, just keep the program running
        logger.info("GPIO handler running with event detection - press Ctrl+C to exit")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        # Clean up
        try:
            GPIO.cleanup()
        except:
            pass
        
        logger.info("GPIO handler stopped")

# Run the GPIO handler when the script is executed directly
if __name__ == "__main__":
    try:
        start_gpio_handler()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
    finally:
        # Make sure we clean up
        try:
            GPIO.cleanup()
        except:
            pass
