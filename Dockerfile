# Use an official Python runtime as a parent image
ARG DOCKER_HUB_URL=dockerhub.itt.aws.odev.com.au

FROM ${DOCKER_HUB_URL}/python:3.12.9-slim

ARG NEXUS_URL
# Redeclare after FROM for use later in ENV/RUN
ARG DOCKER_HUB_URL

# Set environment variables to prevent Python from writing pyc files
# and to enable output buffering for easier logging.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NEXUS_URL=${NEXUS_URL}
ENV DOCKER_HUB_URL=${DOCKER_HUB_URL}


# Make sure NEXUS_URL is available for later RUN commands
RUN echo "Using Nexus URL: ${NEXUS_URL}"  # Debugging step

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Upgrade pip and install Python dependencies
#RUN pip3 install --upgrade pip && pip install -r requirements.txt

RUN pip3 install --upgrade pip --index-url https://${NEXUS_URL}/repository/pypi-central-proxy/simple/ --trusted-host ${NEXUS_URL} && \
    pip install --index-url https://${NEXUS_URL}/repository/pypi-central-proxy/simple/ --trusted-host ${NEXUS_URL} -r requirements.txt  --no-cache-dir

RUN awsv2 --install && \
    ln -s $(command -v awsv2) /usr/local/bin/aws

RUN aws --version

# Copy the rest of your application code into the container
COPY . .

# Expose the port that FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI application using uvicorn.
# Note: --reload is used for development purposes.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
