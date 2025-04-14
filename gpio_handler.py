#!/usr/bin/env python3
"""
CEC Test Tool - Minimal GPIO Handler
Extremely simple approach with direct pin reading
"""
import RPi.GPIO as GPIO
import time
import logging
import cec_control

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gpio_minimal.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gpio_minimal")

# GPIO Pins (BCM mode)
POWER_ON_PIN = 17   # Physical pin 11
POWER_OFF_PIN = 27  # Physical pin 13

# Control flag
running = True

def setup():
    """Very basic GPIO setup"""
    try:
        # Clean up any existing setup
        try:
            GPIO.cleanup()
        except:
            pass
            
        # Set BCM mode
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Configure pins with pull-down
        GPIO.setup(POWER_ON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(POWER_OFF_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        logger.info("Minimal GPIO setup complete")
        return True
    except Exception as e:
        logger.error(f"GPIO setup failed: {e}")
        return False

def start_gpio_handler():
    """Start the minimal GPIO handler"""
    global running
    
    logger.info("Starting minimal GPIO handler")
    
    if not setup():
        logger.error("Failed to set up GPIO")
        return
    
    # Track previous states and press times
    prev_on = GPIO.input(POWER_ON_PIN)
    prev_off = GPIO.input(POWER_OFF_PIN)
    last_on_time = 0
    last_off_time = 0
    
    # Log initial states
    logger.info(f"Initial GPIO states - ON: {prev_on}, OFF: {prev_off}")
    
    try:
        # Main loop
        while running:
            # Read current states
            curr_on = GPIO.input(POWER_ON_PIN)
            curr_off = GPIO.input(POWER_OFF_PIN)
            curr_time = time.time()
            
            # Check for ON button press (LOW to HIGH)
            if curr_on and not prev_on:
                if curr_time - last_on_time > 0.3:  # 300ms debounce
                    logger.info("ON button pressed - Sending power ON command")
                    cec_control.power_on()
                    last_on_time = curr_time
            
            # Check for OFF button press (LOW to HIGH)
            if curr_off and not prev_off:
                if curr_time - last_off_time > 0.3:  # 300ms debounce
                    logger.info("OFF button pressed - Sending power OFF command")
                    cec_control.power_off()
                    last_off_time = curr_time
            
            # Update previous states
            prev_on = curr_on
            prev_off = curr_off
            
            # Brief pause
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        logger.info("GPIO handler stopped by user")
    except Exception as e:
        logger.error(f"Error in GPIO handler: {e}")
    finally:
        try:
            GPIO.cleanup()
            logger.info("GPIO cleaned up")
        except:
            pass

if __name__ == "__main__":
    print("Starting minimal GPIO handler")
    start_gpio_handler()
