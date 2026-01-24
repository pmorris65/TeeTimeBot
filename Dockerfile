FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies required by Playwright/Chromium
RUN yum install -y \
    alsa-lib \
    atk \
    at-spi2-atk \
    at-spi2-core \
    cups-libs \
    dbus-libs \
    gtk3 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    libxkbcommon \
    pango \
    xorg-x11-fonts-100dpi \
    xorg-x11-fonts-75dpi \
    xorg-x11-fonts-cyrillic \
    xorg-x11-fonts-misc \
    xorg-x11-fonts-Type1 \
    xorg-x11-utils \
    nss \
    nspr \
    libdrm \
    mesa-libgbm \
    libgbm \
    && yum clean all

# Set Playwright browser path
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Install Playwright Chromium browser
RUN mkdir -p /opt/playwright && \
    DEBUG=pw:install playwright install chromium

# Copy function code and bot module
COPY clubhouse_bot.py ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "lambda_handler.handler" ]
