import sys
import os
try:
    import reportlab
    import reportlab.pdfgen
    print(f"ReportLab version: {reportlab.__version__}")
    print(f"ReportLab file: {reportlab.__file__}")
    print("SUCCESS: reportlab.pdfgen imported correctly.")
except ImportError as e:
    print(f"ERROR: {e}")
    print(f"sys.path: {sys.path}")
