FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies required by Playwright/Chromium
RUN dnf install -y \
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
    nss \
    nspr \
    libdrm \
    mesa-libgbm \
    && dnf clean all

# Set Playwright browser path
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Install Playwright Chromium browser
RUN mkdir -p /opt/playwright && playwright install chromium

# Copy function code and bot module
COPY clubhouse_bot.py ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY config_reader.py ${LAMBDA_TASK_ROOT}/
COPY parallel_booking.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "lambda_handler.handler" ]
