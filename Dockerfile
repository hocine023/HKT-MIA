FROM apache/airflow:2.10.0-python3.11

USER root

# Install system dependencies: Tesseract OCR (French), Poppler (PDF→image), OpenCV libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-fra \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install Python dependencies
# Pin numpy<2 first to prevent ABI-breaking upgrades, then install the rest
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir "numpy<2" && \
    pip install --no-cache-dir -r /tmp/requirements.txt
