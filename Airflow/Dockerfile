FROM apache/airflow:2.10.2

USER root

# Install git
RUN apt-get update && apt-get install -y git git-lfs

# Install system dependencies for OpenCV and Tesseract
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils

RUN apt-get update && apt-get install -y default-jre

USER 50000