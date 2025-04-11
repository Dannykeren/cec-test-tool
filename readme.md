# CEC Test Tool

A simple HDMI-CEC testing tool for Raspberry Pi with GPIO button support and OLED display feedback.

## Features

- Web-based interface for easy control
- Physical button support (GPIO pins 11 and 13)
- OLED display for status information
- CEC command sending with anti-looping protection
- Easy one-command installation

## Hardware Requirements

- Raspberry Pi (tested on Raspberry Pi 4 with Pi OS Full 32-bit)
- HDMI connection to a CEC-compatible TV or display
- Two momentary push buttons (normally open)
- Small OLED display (I2C, 128x64 or 128x32 pixels)
- Basic wiring components (jumper wires, breadboard)

## Wiring Instructions

1. **GPIO Connections:**
   - Power ON Button: Connect between GPIO 17 (physical pin 11) and 3.3V
   - Power OFF Button: Connect between GPIO 27 (physical pin 13) and 3.3V

2. **I2C OLED Display:**
   - VCC: Connect to 3.3V
   - GND: Connect to ground
   - SCL: Connect to GPIO 3 (physical pin 5)
   - SDA: Connect to GPIO 2 (physical pin 3)

## One-Command Installation

To install the CEC Test Tool, run the following command on your Raspberry Pi:

```bash
curl -sSL https://github.com/dannykeren/cec-test-tool/raw/main/install.sh | sudo bash
```

This will:
- Install all necessary dependencies
- Set up the CEC Test Tool
- Configure the system to start the tool on boot

## Manual Installation

If you prefer to install manually:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/cec-test-tool.git
   cd cec-test-tool
   ```

2. Run the installation script:
   ```bash
   sudo bash install.sh
   ```

## Usage

### Web Interface

Access the web interface by opening a browser and navigating to:
```
http://<your-raspberry-pi-ip>:5000
```

From there you can:
- Send Power ON/OFF commands
- Scan for CEC devices
- Check the power status
- Send custom CEC commands

### Physical Buttons

- Press the button connected to GPIO 17 (pin 11) to power ON
- Press the button connected to GPIO 27 (pin 13) to power OFF

### OLED Display

The OLED display will show:
- The current status of the system
- The last command sent
- The IP address for the web interface

## Troubleshooting

If you encounter any issues:

1. Check the logs:
   ```bash
   sudo journalctl -u cec-test-tool -f
   ```

2. Make sure cec-client is installed and working:
   ```bash
   echo "scan" | cec-client -s -d 1
   ```

3. Verify that the I2C interface is enabled:
   ```bash
   sudo i2cdetect -y 1
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Based on the libCEC library
- Uses Flask for the web interface
- Utilizes Adafruit CircuitPython for the OLED display
