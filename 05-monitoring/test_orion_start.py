import sys
import traceback
import time
import json
import subprocess

# #region agent log
log_path = "/Users/chadcasper/Documents/MLOps Zoomcamp/mlops-zoomcamp/.cursor/debug.log"
def log_debug(location, message, data, hypothesis_id=None):
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": hypothesis_id, "location": location, "message": message, "data": data, "timestamp": int(time.time() * 1000)}) + "\n")
    except:
        pass
# #endregion

# #region agent log
log_debug("test_orion_start.py:imports", "Before Prefect imports", {"python_version": sys.version}, "C")
# #endregion

try:
    # #region agent log
    log_debug("test_orion_start.py:prefect_orion", "Importing prefect.orion", {}, "C")
    # #endregion
    from prefect.orion import api, database, schemas
    # #region agent log
    log_debug("test_orion_start.py:prefect_orion", "Prefect Orion modules imported successfully", {}, "C")
    # #endregion
except Exception as e:
    error_type = type(e).__name__
    error_msg = str(e)
    traceback_str = traceback.format_exc()
    # #region agent log
    log_debug("test_orion_start.py:prefect_orion_error", "Prefect Orion import failed", {"error_type": error_type, "error_message": error_msg, "traceback": traceback_str}, "C")
    # #endregion
    print(f"Orion import error: {error_type}: {error_msg}")
    raise

# #region agent log
log_debug("test_orion_start.py:orion_start", "Attempting to start Orion", {}, "C")
# #endregion

try:
    # Try to import the orion start command
    from prefect.cli import orion
    # #region agent log
    log_debug("test_orion_start.py:orion_cli", "Orion CLI imported", {}, "C")
    # #endregion
    
    # Try to actually start Orion (with timeout to catch initial errors)
    # #region agent log
    log_debug("test_orion_start.py:orion_start_actual", "Starting Orion server", {}, "C")
    # #endregion
    try:
        result = subprocess.run(
            ["prefect", "orion", "start", "--host", "127.0.0.1", "--port", "4200"],
            capture_output=True,
            text=True,
            timeout=3  # Short timeout to catch startup errors
        )
    except subprocess.TimeoutExpired:
        # If it times out, it might have started successfully, but we want to catch errors
        # #region agent log
        log_debug("test_orion_start.py:orion_start_timeout", "Orion start timed out (may have started)", {}, "C")
        # #endregion
        pass
    except Exception as e:
        # #region agent log
        log_debug("test_orion_start.py:orion_start_exception", "Orion start exception", {"error": str(e)}, "C")
        # #endregion
        print(f"Exception starting Orion: {e}")
    
    # Also try importing the start function directly to catch import-time errors
    # #region agent log
    log_debug("test_orion_start.py:orion_start_function", "Importing Orion start function", {}, "C")
    # #endregion
    try:
        from prefect.cli.orion import start
        # #region agent log
        log_debug("test_orion_start.py:orion_start_function", "Orion start function imported", {}, "C")
        # #endregion
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        # #region agent log
        log_debug("test_orion_start.py:orion_start_function_error", "Orion start function import failed", {"error_type": error_type, "error_message": error_msg, "traceback": traceback_str}, "C")
        # #endregion
        print(f"Error importing start function: {error_type}: {error_msg}")
        raise
    
except Exception as e:
    error_type = type(e).__name__
    error_msg = str(e)
    traceback_str = traceback.format_exc()
    # #region agent log
    log_debug("test_orion_start.py:orion_start_error", "Orion start failed", {"error_type": error_type, "error_message": error_msg, "traceback": traceback_str}, "C")
    # #endregion
    print(f"Orion start error: {error_type}: {error_msg}")
