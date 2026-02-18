from enum import Enum


class OutputFormat(str, Enum):
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"
