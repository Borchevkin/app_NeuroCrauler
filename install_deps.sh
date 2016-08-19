#!/bin/sh

echo "[INFO] This script will be trying install required modules by pip3"

# Check presence of the python3
if command -v python3 > /dev/null 2>&1; then
	echo "[GOOD] python3 found on this computer"
else
	echo "[BAD] python3 not found on this computer. Please install python3"
	echo "[EXIT] exit from script"
	exit 1
fi 

# Check presence of pip3
if command -v pip3 > /dev/null 2>&1; then
	echo "[GOOD] pip3 found on this computer"
else
	echo "[BAD] pip3 not found on this computer. Please install pip3"
	echo "[EXIT] exit from script"
	exit 1
fi 

# Check presence of git 
if command -v git > /dev/null 2>&1; then
	echo "[GOOD] git found on this computer"
else
	echo "[BAD] git not found on this computer. Please install git"
	echo "[EXIT] exit from script"
	exit 1
fi 

# Check presence of Xcode - it’s some tricky - for pymunk need clang. For install 
# clang there is simple way - install Xcode
if xcode-select -p > /dev/null 2>&1; then
    echo "[GOOD] Xcode tools found on this computer"
else
	echo "[NOT BAD] Trying to install Xcode tools"
	echo "[GOOD] Invoke popup window. Please select install Xcode"
	xcode-select --install &
fi 

echo "[GOOD] Starting check and install the modules"

# Go to home directory
cd ~

if python3 -c "import pybrain" > /dev/null 2>&1; then
    echo "[GOOD] pybrain is already installed"
else
    echo "[INSTALL] Try to install pybrain"
    # Clone repo with pybrain and install it
    git clone https://github.com/pybrain/pybrain.git
    cd pybrain
    pip3 install . --user
    cd ~
    rm -r -f ~/pybrain
    # Deprecated because in pip3 pybran has legacy version
    #pip3 install pybrain
fi

# Install pyserial for controlling robot over serial port
if python3 -c "import serial" > /dev/null 2>&1; then
    echo "[GOOD] pyserial is already installed"
else
    echo "[INSTALL] Try to install pyserial"
    pip3 install pyserial
fi

# Install pygame
if python3 -c "import pygame" > /dev/null 2>&1; then
    echo "[GOOD] pygame is already installed"
else
    echo "[INSTALL] Try to install pyserial"
    pip3 install pygame
fi

# Install pymunk. If xcode tools is installed there is no problems
if python3 -c "import pymunk" > /dev/null 2>&1; then
    echo "[GOOD] pygame is already installed"
else
    echo "[INSTALL] Try to install pymunk"
    pip3 install pymunk
fi

# End installation
echo "[I HOPE GOOD] End installation. I hope that everything is ok"
