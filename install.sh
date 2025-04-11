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

# Perform full system upgrade
echo "Upgrading system packages..."
apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
apt-get install -y cec-utils i2c-tools python3-venv python3-full

# Enable I2C if not already enabled
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
  echo "Enabling I2C interface..."
  echo "dtparam=i2c_arm=on" >> /boot/config.txt
fi

# Set up installation directory
INSTALL_DIR=/opt/cec-test-tool
mkdir -p $INSTALL_DIR

# Clone the repository if not already done
if [ ! -d "$INSTALL_DIR/.git" ]; then
  echo "Downloading CEC Test Tool..."
  rm -rf $INSTALL_DIR/*
  git clone https://github.com/dannykeren/cec-test-tool.git $INSTALL_DIR
else
  echo "Updating CEC Test Tool..."
  cd $INSTALL_DIR
  git pull
fi

# Create and activate a virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv $INSTALL_DIR/venv
source $INSTALL_DIR/venv/bin/activate

# Install Python dependencies in the virtual environment
echo "Installing Python dependencies..."
pip install flask adafruit-circuitpython-ssd1306 pillow RPi.GPIO

# Get the current non-root user (usually the user who ran sudo)
CURRENT_USER=$(logname || who -m | awk '{print $1}')
CURRENT_GROUP=$(id -gn $CURRENT_USER)

# Use the detected user or fallback to admin if detection fails
USER_TO_SETUP=${CURRENT_USER:-admin}
GROUP_TO_SETUP=${CURRENT_GROUP:-admin}

# Create a systemd service to start the application on boot
echo "Creating systemd service..."
cat > /etc/systemd/system/cec-test-tool.service << EOF
[Unit]
Description=CEC Test Tool
After=network.target

[Service]
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/server.py
WorkingDirectory=$INSTALL_DIR
Restart=always
User=${USER_TO_SETUP}
Group=${GROUP_TO_SETUP}

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl enable cec-test-tool.service

# Set up permissions
echo "Setting up permissions..."

chown -R $USER_TO_SETUP:$GROUP_TO_SETUP $INSTALL_DIR
chmod 777 /dev/gpiomem
usermod -a -G gpio,i2c $USER_TO_SETUP

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
