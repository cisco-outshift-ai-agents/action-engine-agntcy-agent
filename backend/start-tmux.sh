#!/bin/bash

# Create tmux socket directory
mkdir -p /root/.tmux

# Set socket path
TMUX_SOCKET_PATH=${TMUX_SOCKET_PATH:-/root/.tmux/tmux-server}

# Configure tmux if configuration doesn't exist
if [ ! -f /root/.tmux.conf ]; then
  echo "# tmux configuration for persistence and stability" > /root/.tmux.conf
  echo "set -g default-terminal \"screen-256color\"" >> /root/.tmux.conf
  echo "set -g history-limit 100000" >> /root/.tmux.conf
  echo "set -g exit-empty off" >> /root/.tmux.conf
  echo "set -g exit-unattached off" >> /root/.tmux.conf
  echo "set -g destroy-unattached off" >> /root/.tmux.conf
fi

# Kill existing tmux server if it exists but isn't responding
if ! tmux -S $TMUX_SOCKET_PATH list-sessions &>/dev/null && ps aux | grep -v grep | grep tmux | grep $TMUX_SOCKET_PATH > /dev/null; then
  echo "Found stale tmux server, killing it..."
  pkill -f "tmux.*$TMUX_SOCKET_PATH" || true
  sleep 1
fi

# Check if server is running and create default session if needed
if ! tmux -S $TMUX_SOCKET_PATH list-sessions 2>/dev/null | grep -q "terminal-session"; then
  echo "Creating default tmux session: terminal-session"
  tmux -S $TMUX_SOCKET_PATH new-session -d -s terminal-session
  echo "Default session created successfully"
else
  echo "Default tmux session already exists"
fi

# Set proper permissions
chown -R root:root /root/.tmux
chmod -R 755 /root/.tmux

# List all tmux sessions
echo "Active tmux sessions:"
tmux -S $TMUX_SOCKET_PATH list-sessions

# Keep the script running to prevent supervisor from restarting it
tail -f /dev/null
