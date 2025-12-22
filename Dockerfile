FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies for Chrome/Chromium
RUN yum update -y && \
    yum install -y \
    chromium-browser \
    chromium-headless-shell \
    && yum clean all

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy function code and bot module
COPY clubhouse_bot.py ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "lambda_handler.handler" ]
