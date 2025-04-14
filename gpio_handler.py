#!/usr/bin/env python3
"""
Standalone GPIO Handler for CEC Test Tool
Runs as a separate process and uses a simple file-based communication system
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
        logging.FileHandler("/tmp/gpio_handler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gpio_handler")

# GPIO Pins
POWER_ON_PIN = 17   # Physical pin 11
POWER_OFF_PIN = 27  # Physical pin 13

# Flag to control the loop
running = True

# Command file paths
COMMAND_DIR = "/tmp/cec_commands"
ON_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_on_trigger")
OFF_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_off_trigger")

def setup_gpio():
    """Set up GPIO pins"""
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
    """Main monitoring loop for GPIO pins"""
    logger.info("Starting GPIO monitoring loop")
    
    # Initialize state tracking
    last_on_state = GPIO.input(POWER_ON_PIN)
    last_off_state = GPIO.input(POWER_OFF_PIN)
    last_press_time = 0
    on_count = 0
    off_count = 0
    
    # Main loop
    while running:
        try:
            # Read current states
            curr_on_state = GPIO.input(POWER_ON_PIN)
            curr_off_state = GPIO.input(POWER_OFF_PIN)
            curr_time = time.time()
            
            # Check for ON button press (LOW to HIGH)
            if curr_on_state == 1 and last_on_state == 0:
                # Simple debounce
                if curr_time - last_press_time > 0.3:
                    on_count += 1
                    logger.info(f"ON button pressed #{on_count}")
                    trigger_power_on()
                    last_press_time = curr_time
            
            # Check for OFF button press (LOW to HIGH)
            if curr_off_state == 1 and last_off_state == 0:
                # Simple debounce
                if curr_time - last_press_time > 0.3:
                    off_count += 1
                    logger.info(f"OFF button pressed #{off_count}")
                    trigger_power_off()
                    last_press_time = curr_time
            
            # Update previous states
            last_on_state = curr_on_state
            last_off_state = curr_off_state
            
            # Sleep briefly
            time.sleep(0.05)
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            time.sleep(1)
            
            # Try to recover
            try:
                setup_gpio()
                last_on_state = GPIO.input(POWER_ON_PIN)
                last_off_state = GPIO.input(POWER_OFF_PIN)
            except:
                pass

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
        # Start monitoring loop
        gpio_monitoring_loop()
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
