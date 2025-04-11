#!/bin/bash

echo "========================================="
echo "     CEC Test Tool Installation Script"
echo "========================================="

# Exit on any error
set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

# Update package lists
echo "Updating package lists..."
apt-get update

# Install required packages
echo "Installing required packages..."
apt-get install -y python3-pip python3-gpiozero python3-flask cec-utils python3-smbus i2c-tools

# Enable I2C if not already enabled
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
  echo "Enabling I2C interface..."
  echo "dtparam=i2c_arm=on" >> /boot/config.txt
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install flask adafruit-circuitpython-ssd1306 pillow pycdcj RPi.GPIO

# Create a systemd service to start the application on boot
echo "Creating systemd service..."
cat > /etc/systemd/system/cec-test-tool.service << EOF
[Unit]
Description=CEC Test Tool
After=network.target

[Service]
ExecStart=/usr/bin/python3 $(pwd)/server.py
WorkingDirectory=$(pwd)
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl enable cec-test-tool.service

# Set up permissions
echo "Setting up permissions..."
usermod -a -G gpio,i2c pi

echo "========================================="
echo "Installation complete!"
echo "The CEC Test Tool will start automatically on next boot."
echo "To start it now, run: sudo systemctl start cec-test-tool"
echo "To view logs, run: sudo journalctl -u cec-test-tool -f"
echo "========================================="

# Ask to reboot
read -p "A reboot is recommended. Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Rebooting..."
  reboot
fi
