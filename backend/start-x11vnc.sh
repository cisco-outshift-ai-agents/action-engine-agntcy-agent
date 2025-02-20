#!/bin/bash

# Reload systemd manager configuration
systemctl daemon-reload

# Enable x11vnc service
systemctl enable x11vnc.service

# Start x11vnc service
systemctl start x11vnc.service

# Check the status of x11vnc service
systemctl status x11vnc.service
