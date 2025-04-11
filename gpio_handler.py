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
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Set up the input pins with pull-down resistors
    # Buttons will be connected between pins and 3.3V (active high)
    GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    # Add event detection for both buttons (rising edge = button press)
    GPIO.add_event_detect(POWER_ON_PIN, GPIO.RISING, 
                         callback=power_on_callback, bouncetime=300)
    GPIO.add_event_detect(POWER_OFF_PIN, GPIO.RISING, 
                         callback=power_off_callback, bouncetime=300)
    
    logger.info("GPIO setup complete")

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

def start_gpio_handler():
    """Start the GPIO handler"""
    try:
        setup_gpio()
        logger.info("GPIO handler started. Press Ctrl+C to exit.")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("GPIO handler stopped by user")
    except Exception as e:
        logger.error(f"GPIO handler error: {e}")
    finally:
        cleanup()

# Run the GPIO handler when the script is executed directly
if __name__ == "__main__":
    print("Starting GPIO Handler...")
    start_gpio_handler()
