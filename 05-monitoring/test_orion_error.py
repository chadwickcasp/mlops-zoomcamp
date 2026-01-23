#!/usr/bin/env python
"""Test script to capture Orion startup errors"""
import sys
import traceback
import json
import time

log_path = "/Users/chadcasper/Documents/MLOps Zoomcamp/mlops-zoomcamp/.cursor/debug.log"

def log_debug(location, message, data, hypothesis_id=None):
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except:
        pass

log_debug("test_orion_error.py:start", "Starting Orion error test", {"python_version": sys.version}, "C")

# Try importing Orion server components
try:
    log_debug("test_orion_error.py:import_orion_server", "Importing Orion server", {}, "C")
    from prefect.orion.server.server import create_app
    log_debug("test_orion_error.py:import_orion_server", "Orion server imported", {}, "C")
except Exception as e:
    error_type = type(e).__name__
    error_msg = str(e)
    traceback_str = traceback.format_exc()
    log_debug("test_orion_error.py:import_orion_server_error", "Orion server import failed", {
        "error_type": error_type,
        "error_message": error_msg,
        "traceback": traceback_str
    }, "C")
    print(f"ERROR importing Orion server: {error_type}: {error_msg}")
    print(traceback_str)
    sys.exit(1)

# Try importing settings
try:
    log_debug("test_orion_error.py:import_settings", "Importing Prefect settings", {}, "C")
    from prefect.settings import PREFECT_ORION_API_HOST, PREFECT_ORION_API_PORT
    log_debug("test_orion_error.py:import_settings", "Settings imported", {}, "C")
except Exception as e:
    error_type = type(e).__name__
    error_msg = str(e)
    traceback_str = traceback.format_exc()
    log_debug("test_orion_error.py:import_settings_error", "Settings import failed", {
        "error_type": error_type,
        "error_message": error_msg,
        "traceback": traceback_str
    }, "C")
    print(f"ERROR importing settings: {error_type}: {error_msg}")
    print(traceback_str)
    sys.exit(1)

# Try creating the app
try:
    log_debug("test_orion_error.py:create_app", "Creating Orion app", {}, "C")
    app = create_app()
    log_debug("test_orion_error.py:create_app", "Orion app created", {}, "C")
except Exception as e:
    error_type = type(e).__name__
    error_msg = str(e)
    traceback_str = traceback.format_exc()
    log_debug("test_orion_error.py:create_app_error", "App creation failed", {
        "error_type": error_type,
        "error_message": error_msg,
        "traceback": traceback_str
    }, "C")
    print(f"ERROR creating app: {error_type}: {error_msg}")
    print(traceback_str)
    sys.exit(1)

# Try importing database
try:
    log_debug("test_orion_error.py:import_database", "Importing database", {}, "C")
    from prefect.orion.database import get_database_engine
    log_debug("test_orion_error.py:import_database", "Database imported", {}, "C")
except Exception as e:
    error_type = type(e).__name__
    error_msg = str(e)
    traceback_str = traceback.format_exc()
    log_debug("test_orion_error.py:import_database_error", "Database import failed", {
        "error_type": error_type,
        "error_message": error_msg,
        "traceback": traceback_str
    }, "C")
    print(f"ERROR importing database: {error_type}: {error_msg}")
    print(traceback_str)
    sys.exit(1)

print("✓ All Orion components imported successfully")
log_debug("test_orion_error.py:success", "All imports successful", {}, "C")
