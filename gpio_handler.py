#!/usr/bin/env python3
"""
Standalone GPIO Handler for CEC Test Tool
With improved recovery from 'GPIO busy' errors
"""
import RPi.GPIO as GPIO
import time
import logging
import os
import json
import subprocess
import sys

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

# Flag to control the loop
running = True

# Command file paths
COMMAND_DIR = "/tmp/cec_commands"
ON_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_on_trigger")
OFF_COMMAND_FILE = os.path.join(COMMAND_DIR, "power_off_trigger")

def kill_other_instances():
    """Attempt to kill other instances of this script"""
    try:
        # Get our PID
        our_pid = os.getpid()
        
        # Find all python processes running our script
        cmd = f"ps aux | grep 'python.*gpio_handler.py' | grep -v grep | awk '{{print $2}}'"
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output = proc.stdout.read().decode('utf-8').strip()
        
        # Kill other instances
        if output:
            for pid in output.split('\n'):
                pid = pid.strip()
                if pid and int(pid) != our_pid:
                    logger.info(f"Killing other instance with PID {pid}")
                    try:
                        os.kill(int(pid), 9)
                    except:
                        pass
        
        # Wait a moment for processes to terminate
        time.sleep(1)
        return True
    except Exception as e:
        logger.error(f"Error killing other instances: {e}")
        return False

def reset_gpio_system():
    """Attempt to reset the GPIO system"""
    try:
        # Try cleaning up GPIO
        try:
            GPIO.cleanup()
        except:
            pass
        
        # Force reset GPIO module
        GPIO.setwarnings(False)
        
        # Try unloading and reloading the GPIO module
        try:
            if hasattr(GPIO, "cleanup_all"):
                GPIO.cleanup_all()
        except:
            pass
            
        # Wait for reset to take effect
        time.sleep(2)
        
        logger.info("GPIO system reset attempt completed")
        return True
    except Exception as e:
        logger.error(f"Error resetting GPIO system: {e}")
        return False

def setup_gpio():
    """Set up GPIO pins for polling"""
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Simple setup
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
    """Basic polling loop that just checks HIGH status"""
    logger.info("Starting basic GPIO monitoring loop")
    
    on_count = 0
    off_count = 0
    
    # Track button states to detect changes
    last_on_high = False
    last_off_high = False
    
    # Main loop
    while running:
        try:
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
            
            # Slow down the loop
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            time.sleep(1)

def start_gpio_handler():
    """Main entry point for GPIO handler"""
    logger.info("Starting standalone GPIO handler")
    
    # Kill other instances first
    kill_other_instances()
    
    # Reset GPIO system
    reset_gpio_system()
    
    # Setup
    if not setup_gpio():
        logger.error("Failed to set up GPIO pins")
        logger.info("Attempting recovery...")
        
        # Try one more time after a delay
        time.sleep(3)
        reset_gpio_system()
        if not setup_gpio():
            logger.error("GPIO setup failed after recovery attempt")
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
