#!/usr/bin/env python3
"""
Standalone GPIO Handler for CEC Test Tool
Using lock file to prevent multiple instances
"""
import RPi.GPIO as GPIO
import time
import logging
import os
import json
import subprocess
import sys
import fcntl
import signal
import atexit

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Log to console only to avoid permission issues
    ]
)
logger = logging.getLogger("gpio_handler")

# Lock file path
LOCK_FILE = "/tmp/gpio_handler.lock"

# GPIO Pins
POWER_ON_PIN = 17   # Physical pin 11
POWER_OFF_PIN = 27  # Physical pin 13

# Command file paths
COMMAND_DIR = "/tmp/cec_commands"
ON_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_on_trigger")
OFF_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_off_trigger")

# Global variables
lock_file_handle = None

def acquire_lock():
    """Try to acquire a lock file to ensure we're the only instance running"""
    global lock_file_handle
    
    try:
        # Open the lock file
        lock_file_handle = open(LOCK_FILE, 'w')
        
        # Try to get an exclusive lock (non-blocking)
        fcntl.flock(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        # Write our PID to the lock file
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
        
        logger.info(f"Lock acquired, PID {os.getpid()}")
        return True
        
    except IOError:
        # Another instance has the lock
        logger.error("Another instance is already running (lock file exists)")
        if lock_file_handle:
            lock_file_handle.close()
        return False
    except Exception as e:
        logger.error(f"Lock acquisition error: {e}")
        if lock_file_handle:
            lock_file_handle.close()
        return False

def release_lock():
    """Release the lock file"""
    global lock_file_handle
    
    try:
        if lock_file_handle:
            # Release the lock and close the file
            fcntl.flock(lock_file_handle, fcntl.LOCK_UN)
            lock_file_handle.close()
            
            # Try to remove the lock file
            try:
                os.remove(LOCK_FILE)
            except:
                pass
                
            logger.info("Lock released")
    except Exception as e:
        logger.error(f"Error releasing lock: {e}")

def cleanup_and_exit(signal_num=None, frame=None):
    """Clean up resources and exit"""
    logger.info("Cleaning up resources...")
    
    # Clean up GPIO
    try:
        GPIO.cleanup()
    except:
        pass
    
    # Release lock
    release_lock()
    
    logger.info("Cleanup complete, exiting")
    sys.exit(0)

def setup_gpio():
    """Set up GPIO pins"""
    try:
        # First try to clean up
        try:
            GPIO.cleanup()
        except:
            pass
            
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        logger.info(f"GPIO pins configured: ON={POWER_ON_PIN}, OFF={POWER_OFF_PIN}")
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
        except:
            pass
            
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
        except:
            pass
            
    except Exception as e:
        logger.error(f"Failed to create power OFF trigger: {e}")

def gpio_monitoring_loop():
    """Monitor GPIO pins for button presses"""
    logger.info("Starting GPIO monitoring loop")
    
    # Button press counters
    on_count = 0
    off_count = 0
    
    # Track button states to detect changes
    last_on_high = GPIO.input(POWER_ON_PIN) == 1
    last_off_high = GPIO.input(POWER_OFF_PIN) == 1
    
    # Main loop
    try:
        while True:
            # Read current button states
            on_is_high = GPIO.input(POWER_ON_PIN) == 1
            off_is_high = GPIO.input(POWER_OFF_PIN) == 1
            
            # ON button handling - trigger only when it BECOMES high
            if on_is_high and not last_on_high:
                on_count += 1
                logger.info(f"ON button pressed #{on_count}")
                trigger_power_on()
            
            # OFF button handling - trigger only when it BECOMES high
            if off_is_high and not last_off_high:
                off_count += 1
                logger.info(f"OFF button pressed #{off_count}")
                trigger_power_off()
            
            # Update button states
            last_on_high = on_is_high
            last_off_high = off_is_high
            
            # Brief delay
            time.sleep(0.1)
            
    except Exception as e:
        logger.error(f"Error in monitoring loop: {e}")
        return False
        
    return True

def start_gpio_handler():
    """Main entry point for GPIO handler"""
    logger.info("Starting standalone GPIO handler")
    
    # Set up signal handlers for clean exit
    signal.signal(signal.SIGINT, cleanup_and_exit)  # Ctrl+C
    signal.signal(signal.SIGTERM, cleanup_and_exit)  # termination
    atexit.register(cleanup_and_exit)  # Normal exit
    
    # Try to acquire lock
    if not acquire_lock():
        logger.error("Cannot acquire lock, exiting")
        sys.exit(1)
    
    # Set up GPIO pins
    retry_count = 0
    while retry_count < 3:
        if setup_gpio():
            break
        logger.info(f"GPIO setup failed, retrying ({retry_count+1}/3)...")
        time.sleep(2)
        retry_count += 1
    
    if retry_count >= 3:
        logger.error("Failed to set up GPIO after multiple attempts")
        cleanup_and_exit()
    
    # Set up command directory
    if not setup_command_dir():
        logger.error("Failed to set up command directory")
        cleanup_and_exit()
    
    # Start monitoring loop
    logger.info("Starting GPIO monitoring")
    try:
        gpio_monitoring_loop()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    
    # Clean up
    cleanup_and_exit()

# Run the GPIO handler when the script is executed directly
if __name__ == "__main__":
    try:
        start_gpio_handler()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
    finally:
        # Make sure we clean up
        cleanup_and_exit()
