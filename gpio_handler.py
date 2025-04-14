#!/usr/bin/env python3
"""
CEC Test Tool - GPIO Handler (Debug Version)
Simplified approach for maximum reliability
"""
import RPi.GPIO as GPIO
import time
import logging
import threading
import cec_control

# Set up logging with more detailed debug info
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose logging
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

# Button state tracking
button_states = {
    'power_on': False,
    'power_off': False
}

# Flag to control the polling loop
running = True

# Debug counters
debug_counters = {
    'power_on_presses': 0,
    'power_off_presses': 0,
    'polling_cycles': 0
}

def setup_gpio():
    """Initialize the GPIO pins with basic configuration"""
    try:
        # Log the GPIO library version
        logger.info(f"Using RPi.GPIO version: {GPIO.VERSION}")
        
        # Use BCM pin numbering
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Set up the input pins with pull-down resistors
        # This means the pins will read LOW when the button is not pressed
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Log the initial state of the pins
        on_state = GPIO.input(POWER_ON_PIN)
        off_state = GPIO.input(POWER_OFF_PIN)
        logger.info(f"Initial GPIO states - Power ON pin: {on_state}, Power OFF pin: {off_state}")
        
        logger.info("GPIO setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"GPIO setup failed with exception: {e}")
        return False

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

def handle_power_on():
    """Handle power on button press with extensive debugging"""
    log_button_press('power_on')
    try:
        logger.debug("Calling cec_control.power_on()")
        response = cec_control.power_on()
        logger.info(f"CEC power ON response: {response[:50]}...")  # Log first 50 chars
    except Exception as e:
        logger.error(f"Exception during power ON command: {e}")

def handle_power_off():
    """Handle power off button press with extensive debugging"""
    log_button_press('power_off')
    try:
        logger.debug("Calling cec_control.power_off()")
        response = cec_control.power_off()
        logger.info(f"CEC power OFF response: {response[:50]}...")  # Log first 50 chars
    except Exception as e:
        logger.error(f"Exception during power OFF command: {e}")

def poll_gpio_pins():
    """Poll GPIO pins in a simple, reliable way"""
    # Initialize previous states
    prev_on_state = GPIO.input(POWER_ON_PIN)
    prev_off_state = GPIO.input(POWER_OFF_PIN)
    
    # Log initial states
    logger.info(f"Starting GPIO polling with initial states - ON: {prev_on_state}, OFF: {prev_off_state}")
    
    # Track time for periodic status updates
    last_status_time = time.time()
    
    while running:
        try:
            # Update debug counter
            debug_counters['polling_cycles'] += 1
            
            # Read current button states
            current_on_state = GPIO.input(POWER_ON_PIN)
            current_off_state = GPIO.input(POWER_OFF_PIN)
            
            # Check for button press (transition from LOW to HIGH)
            if current_on_state == 1 and prev_on_state == 0:
                logger.debug("ON button state change detected (0->1)")
                # Set button state
                button_states['power_on'] = True
                # Handle the button press in the polling thread directly
                handle_power_on()
            
            # Check for button release (transition from HIGH to LOW)
            elif current_on_state == 0 and prev_on_state == 1:
                logger.debug("ON button state change detected (1->0)")
                button_states['power_on'] = False
            
            # Check for OFF button press
            if current_off_state == 1 and prev_off_state == 0:
                logger.debug("OFF button state change detected (0->1)")
                button_states['power_off'] = True
                handle_power_off()
            
            # Check for OFF button release
            elif current_off_state == 0 and prev_off_state == 1:
                logger.debug("OFF button state change detected (1->0)")
                button_states['power_off'] = False
            
            # Update previous states
            prev_on_state = current_on_state
            prev_off_state = current_off_state
            
            # Log periodic status update (every 30 seconds)
            current_time = time.time()
            if current_time - last_status_time > 30:
                on_pin = GPIO.input(POWER_ON_PIN)
                off_pin = GPIO.input(POWER_OFF_PIN)
                logger.info(f"GPIO status - ON pin: {on_pin}, OFF pin: {off_pin}, " +
                            f"ON presses: {debug_counters['power_on_presses']}, " +
                            f"OFF presses: {debug_counters['power_off_presses']}, " +
                            f"Poll cycles: {debug_counters['polling_cycles']}")
                last_status_time = current_time
            
            # Short sleep to reduce CPU usage but remain responsive
            time.sleep(0.03)
            
        except Exception as e:
            logger.error(f"Exception in GPIO polling loop: {e}")
            time.sleep(0.5)  # Sleep longer on error

def start_gpio_handler():
    """Start the GPIO handler with improved error handling"""
    global running
    
    logger.info("Starting GPIO handler...")
    
    try:
        # Setup GPIO pins
        if not setup_gpio():
            logger.error("GPIO setup failed, cannot continue")
            return
        
        # Start the polling loop in the main thread
        logger.info("Starting GPIO polling loop")
        running = True
        poll_gpio_pins()
        
    except KeyboardInterrupt:
        logger.info("GPIO handler stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error in GPIO handler: {e}")
    finally:
        # Clean up
        running = False
        try:
            GPIO.cleanup()
            logger.info("GPIO resources cleaned up")
        except Exception as e:
            logger.error(f"Error during GPIO cleanup: {e}")

# Run the GPIO handler when the script is executed directly
if __name__ == "__main__":
    print("Starting GPIO Handler in debug mode...")
    start_gpio_handler()
