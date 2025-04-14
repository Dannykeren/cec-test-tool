#!/usr/bin/env python3
"""
CEC Test Tool - GPIO Handler
Handles the physical GPIO buttons for CEC control
"""
import RPi.GPIO as GPIO
import time
import logging
from threading import Thread, Lock
import cec_control

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gpio_handler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gpio_handler")

# GPIO Pins (BCM mode)
POWER_ON_PIN = 17   # Physical pin 11
POWER_OFF_PIN = 27  # Physical pin 13

# Button debounce time in seconds
DEBOUNCE_TIME = 0.3

# Thread safety
button_lock = Lock()
last_button_press = 0

def setup_gpio():
    """Initialize the GPIO pins"""
    try:
        logger.info("Setting up GPIO pins...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Set up the input pins with pull-down resistors
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        logger.info("GPIO setup complete - using polling method only")
        return True
    except Exception as e:
        logger.error(f"GPIO setup failed: {e}")
        return False

def is_debounced():
    """Check if enough time has passed since the last button press"""
    global last_button_press
    current_time = time.time()
    if current_time - last_button_press < DEBOUNCE_TIME:
        return False
    last_button_press = current_time
    return True

def power_on_callback(channel):
    """Callback for power ON button press"""
    if not is_debounced():
        return
    
    with button_lock:
        logger.info("Power ON button pressed")
        response = cec_control.power_on()
        logger.info(f"CEC response: {response}")

def power_off_callback(channel):
    """Callback for power OFF button press"""
    if not is_debounced():
        return
    
    with button_lock:
        logger.info("Power OFF button pressed")
        response = cec_control.power_off()
        logger.info(f"CEC response: {response}")

def cleanup():
    """Clean up GPIO resources"""
    GPIO.cleanup()
    logger.info("GPIO resources cleaned up")

def manual_poll_gpio():
    """Manually poll GPIO pins as a backup"""
    prev_on_state = GPIO.input(POWER_ON_PIN)  # Initialize with current state
    prev_off_state = GPIO.input(POWER_OFF_PIN)  # Initialize with current state
    
    while True:
        try:
            on_state = GPIO.input(POWER_ON_PIN)
            off_state = GPIO.input(POWER_OFF_PIN)
            
            # Check for state changes (0 to 1 = button pressed)
            if on_state == 1 and prev_on_state == 0:
                logger.debug("ON button press detected in polling loop")
                power_on_callback(POWER_ON_PIN)
            
            if off_state == 1 and prev_off_state == 0:
                logger.debug("OFF button press detected in polling loop")
                power_off_callback(POWER_OFF_PIN)
            
            # Update previous states
            prev_on_state = on_state
            prev_off_state = off_state
            
            # Sleep to reduce CPU usage
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error in GPIO polling loop: {e}")
            time.sleep(1)

def start_gpio_handler():
    """Start the GPIO handler"""
    try:
        if not setup_gpio():
            logger.error("Failed to set up GPIO. Cannot continue.")
            return
        
        logger.info("GPIO handler started with both event detection and polling")
        
        # Start the polling thread as a backup
        polling_thread = Thread(target=manual_poll_gpio)
        polling_thread.daemon = True
        polling_thread.start()
        
        # Keep the script running
        while True:
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("GPIO handler stopped by user")
    except Exception as e:
        logger.error(f"GPIO handler error: {e}")
    finally:
        GPIO.cleanup()
        logger.info("GPIO resources cleaned up")

# Run the GPIO handler when the script is executed directly
if __name__ == "__main__":
    print("Starting GPIO Handler...")
    start_gpio_handler()
