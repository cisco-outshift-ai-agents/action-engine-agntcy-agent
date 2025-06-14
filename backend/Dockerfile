FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential
RUN apt-get update && apt-get install -y \
    wget \
    netcat-traditional \
    gnupg \
    curl \
    libpq-dev \
    unzip \
    tmux \
    xvfb \
    libgconf-2-4 \
    libxss1 \
    libnss3 \
    libnspr4 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    fonts-liberation \
    dbus \
    dbus-x11 \
    xauth \
    feh \ 
    x11vnc \
    tigervnc-tools \
    supervisor \
    net-tools \
    procps \
    git \
    python3-numpy \
    fontconfig \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc \
    && git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Install Chrome
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \ 
    && apt-get install -y google-chrome-stable

# Set up working directory
WORKDIR /app

# Copy requirements and install Python dependencies
# Copy local packages first
COPY workflow_srv /app/workflow_srv
COPY acp_spec /app/acp_spec

# Install all dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install -e ./workflow_srv

# Install Playwright and browsers with system dependencies
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps chromium
RUN playwright install-deps

# Install D-Bus
RUN apt-get update && apt-get install -y dbus
# Ensure /run/dbus directory exists and set permissions
RUN mkdir -p /run/dbus && chmod 755 /run/dbus
# Set environment variables for D-Bus
ENV DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
# Start D-Bus service
RUN dbus-uuidgen > /etc/machine-id && service dbus start

# Create tmux directory for socket and make it persistent
RUN mkdir -p /root/.tmux
VOLUME /root/.tmux

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV BROWSER_USE_LOGGING_LEVEL=info
ENV CHROME_PATH=/usr/bin/google-chrome
ENV ANONYMIZED_TELEMETRY=false
ENV DISPLAY=:99
ENV RESOLUTION=1920x1080x24
ENV VNC_PASSWORD=youvncpassword
ENV CHROME_PERSISTENT_SESSION=true
ENV RESOLUTION_WIDTH=1920
ENV RESOLUTION_HEIGHT=1080
ENV VNC_PORT=5900
ENV TMUX_SOCKET_PATH=/root/.tmux/tmux-server

# Set up supervisor configuration
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start-tmux.sh /app/
RUN chmod +x /app/start-tmux.sh

EXPOSE 7788 6080 5900 9222
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
