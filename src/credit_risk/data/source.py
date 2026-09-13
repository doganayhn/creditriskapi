"""Verified V1 source identity; no network activity at import time."""

DATASET_NAME = "Default of Credit Card Clients"
SOURCE_PAGE = "https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients"
DOWNLOAD_URL = "https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip"
RAW_FILENAME = "default of credit card clients.xls"
# Measured from the official XLS on 2026-09-13, not a publisher-supplied checksum.
EXPECTED_SHA256 = "30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933"
DOI = "10.24432/C55S3H"
LICENSE = "CC BY 4.0"
ATTRIBUTION = "Yeh, I. (2009). Default of Credit Card Clients [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C55S3H."
TARGET = "default_next_month"
ORIGINAL_TARGET = "default payment next month"
