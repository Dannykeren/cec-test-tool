#!/usr/bin/env python3
"""
CEC Test Tool - GPIO Handler (Simplified Version)
Very basic approach for maximum reliability
"""
import RPi.GPIO as GPIO
import time
import logging
import threading
import cec_control

# Set up logging
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

# Flag to control the loop
running = True

# Debug counters
debug_counters = {
    'power_on_presses': 0,
    'power_off_presses': 0
}

# Last time each button was pressed (for debouncing)
last_press_time = {
    'power_on': 0,
    'power_off': 0
}

def setup_gpio():
    """Initialize the GPIO pins with basic configuration"""
    try:
        # Use BCM pin numbering
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Set up the input pins with pull-down resistors
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        logger.info("GPIO pins configured successfully")
        return True
    except Exception as e:
        logger.error(f"GPIO setup failed: {e}")
        return False

def handle_power_on():
    """Handle power on button press"""
    debug_counters['power_on_presses'] += 1
    logger.info(f"POWER ON button pressed - Press #{debug_counters['power_on_presses']}")
    
    try:
        response = cec_control.power_on()
        logger.info(f"CEC power ON response received")
    except Exception as e:
        logger.error(f"Error in power ON command: {e}")

def handle_power_off():
    """Handle power off button press"""
    debug_counters['power_off_presses'] += 1
    logger.info(f"POWER OFF button pressed - Press #{debug_counters['power_off_presses']}")
    
    try:
        response = cec_control.power_off()
        logger.info(f"CEC power OFF response received")
    except Exception as e:
        logger.error(f"Error in power OFF command: {e}")

def simple_button_loop():
    """Super simple button reading loop"""
    # Reset button states on startup
    prev_on_state = 0
    prev_off_state = 0
    
    # For status logging
    last_status_time = time.time()
    
    logger.info("Starting simple button polling loop")
    
    while running:
        try:
            current_time = time.time()
            
            # Read current button states
            on_state = GPIO.input(POWER_ON_PIN)
            off_state = GPIO.input(POWER_OFF_PIN)
            
            # Check for ON button press (transition from LOW to HIGH)
            if on_state == 1 and prev_on_state == 0:
                # Simple debounce - at least 200ms since last press
                if current_time - last_press_time['power_on'] > 0.2:
                    handle_power_on()
                    last_press_time['power_on'] = current_time
            
            # Check for OFF button press (transition from LOW to HIGH)
            if off_state == 1 and prev_off_state == 0:
                # Simple debounce - at least 200ms since last press
                if current_time - last_press_time['power_off'] > 0.2:
                    handle_power_off()
                    last_press_time['power_off'] = current_time
            
            # Update previous states for next iteration
            prev_on_state = on_state
            prev_off_state = off_state
            
            # Log status every 30 seconds
            if current_time - last_status_time > 30:
                logger.info(f"GPIO status - ON pin: {on_state}, OFF pin: {off_state}, " +
                           f"ON presses: {debug_counters['power_on_presses']}, " +
                           f"OFF presses: {debug_counters['power_off_presses']}")
                last_status_time = current_time
            
            # Brief sleep to reduce CPU usage
            time.sleep(0.05)
            
        except Exception as e:
            logger.error(f"Error in button loop: {e}")
            time.sleep(0.5)
            
            # Try to recover
            try:
                setup_gpio()
                prev_on_state = 0
                prev_off_state = 0
            except:
                pass

def start_gpio_handler():
    """Start the GPIO handler"""
    global running
    
    logger.info("Starting simplified GPIO handler...")
    
    try:
        # Initialize GPIO
        if not setup_gpio():
            logger.error("Failed to set up GPIO, cannot continue")
            return
        
        # Start the button loop
        running = True
        simple_button_loop()
        
    except KeyboardInterrupt:
        logger.info("GPIO handler stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error in GPIO handler: {e}")
    finally:
        # Clean up
        running = False
        try:
            GPIO.cleanup()
        except:
            pass

# Run the GPIO handler when the script is executed directly
if __name__ == "__main__":
    print("Starting simplified GPIO handler...")
    start_gpio_handler()
