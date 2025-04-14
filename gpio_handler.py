#!/usr/bin/env python3
"""
CEC Test Tool - GPIO Handler (Callback Version)
Using event-driven callbacks for button detection
"""
import RPi.GPIO as GPIO
import time
import logging
import threading
import cec_control

# Set up logging with more detailed debug info
logging.basicConfig(
    level=logging.DEBUG,
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
DEBOUNCE_TIME = 300  # milliseconds

# Flag to control the loop
running = True

# Debug counters
debug_counters = {
    'power_on_presses': 0,
    'power_off_presses': 0
}

def log_button_press(button_name):
    """Log detailed information about a button press"""
    if button_name == 'power_on':
        debug_counters['power_on_presses'] += 1
        count = debug_counters['power_on_presses']
        logger.info(f"POWER ON button pressed - Press #{count}")
    else:
        debug_counters['power_off_presses'] += 1
        count = debug_counters['power_off_presses']
        logger.info(f"POWER OFF button pressed - Press #{count}")
    
    # Log the current state of both pins for debugging
    on_state = GPIO.input(POWER_ON_PIN)
    off_state = GPIO.input(POWER_OFF_PIN)
    logger.debug(f"Current GPIO states - Power ON pin: {on_state}, Power OFF pin: {off_state}")

def power_on_callback(channel):
    """Callback function for power on button"""
    # Check if the button is actually pressed (HIGH)
    if GPIO.input(POWER_ON_PIN):
        log_button_press('power_on')
        try:
            logger.debug("Calling cec_control.power_on() from callback")
            response = cec_control.power_on()
            logger.info(f"CEC power ON response: {response[:50] if response else 'No response'}...")
        except Exception as e:
            logger.error(f"Exception during power ON command: {e}")

def power_off_callback(channel):
    """Callback function for power off button"""
    # Check if the button is actually pressed (HIGH)
    if GPIO.input(POWER_OFF_PIN):
        log_button_press('power_off')
        try:
            logger.debug("Calling cec_control.power_off() from callback")
            response = cec_control.power_off()
            logger.info(f"CEC power OFF response: {response[:50] if response else 'No response'}...")
        except Exception as e:
            logger.error(f"Exception during power OFF command: {e}")

def setup_gpio():
    """Initialize the GPIO pins with event detection"""
    try:
        # Clean up any previous setup
        GPIO.cleanup()
        
        # Log the GPIO library version
        logger.info(f"Using RPi.GPIO version: {GPIO.VERSION}")
        
        # Use BCM pin numbering
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Set up the input pins with pull-down resistors
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Add event detection with debounce
        GPIO.add_event_detect(POWER_ON_PIN, GPIO.RISING, 
                             callback=power_on_callback, 
                             bouncetime=DEBOUNCE_TIME)
        
        GPIO.add_event_detect(POWER_OFF_PIN, GPIO.RISING, 
                             callback=power_off_callback, 
                             bouncetime=DEBOUNCE_TIME)
        
        # Log the initial state of the pins
        on_state = GPIO.input(POWER_ON_PIN)
        off_state = GPIO.input(POWER_OFF_PIN)
        logger.info(f"Initial GPIO states - Power ON pin: {on_state}, Power OFF pin: {off_state}")
        
        logger.info("GPIO setup with event detection completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"GPIO setup failed with exception: {e}")
        return False

def start_gpio_monitor():
    """Start a simple monitoring loop to keep the thread alive and log status"""
    logger.info("Starting GPIO monitoring thread")
    
    # Track time for periodic status updates
    last_status_time = time.time()
    
    while running:
        try:
            # Current time for status updates
            current_time = time.time()
            
            # Log periodic status update (every 30 seconds)
            if current_time - last_status_time > 30:
                on_pin = GPIO.input(POWER_ON_PIN)
                off_pin = GPIO.input(POWER_OFF_PIN)
                logger.info(f"GPIO status - ON pin: {on_pin}, OFF pin: {off_pin}, " +
                            f"ON presses: {debug_counters['power_on_presses']}, " +
                            f"OFF presses: {debug_counters['power_off_presses']}")
                last_status_time = current_time
            
            # Check that event detection is still active
            if not GPIO.event_detected(POWER_ON_PIN) and not GPIO.event_detected(POWER_OFF_PIN):
                pass  # This just tests that the function can be called
            
            # Sleep to reduce CPU usage
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Exception in GPIO monitoring loop: {e}")
            time.sleep(5)  # Sleep longer on error
            
            # Try to recover by reinitializing
            try:
                setup_gpio()
                logger.info("Reinitialized GPIO after error")
            except Exception as recovery_error:
                logger.error(f"Failed to recover from monitoring error: {recovery_error}")

def start_gpio_handler():
    """Start the GPIO handler with event detection"""
    global running
    
    logger.info("Starting GPIO handler with event detection...")
    
    try:
        # Setup GPIO pins with event detection
        if not setup_gpio():
            logger.error("GPIO setup failed, cannot continue")
            return
        
        # Start the monitoring loop
        logger.info("Starting GPIO monitoring loop")
        running = True
        start_gpio_monitor()
        
    except KeyboardInterrupt:
        logger.info("GPIO handler stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error in GPIO handler: {e}")
    finally:
        # Clean up resources
        running = False
        cleanup_gpio()

def cleanup_gpio():
    """Clean up GPIO resources"""
    try:
        GPIO.cleanup()
        logger.info("GPIO resources cleaned up")
    except Exception as e:
        logger.error(f"Error during GPIO cleanup: {e}")

# Run the GPIO handler when the script is executed directly
if __name__ == "__main__":
    print("Starting GPIO Handler with event detection...")
    try:
        start_gpio_handler()
    finally:
        cleanup_gpio()
