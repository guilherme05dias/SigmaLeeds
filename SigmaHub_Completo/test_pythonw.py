import sys, os
log = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pythonw_debug.log')
if sys.stdout is None:
    sys.stdout = open(log, 'w')
if sys.stderr is None:
    sys.stderr = sys.stdout
try:
    print("stdout/stderr OK")
    print(f"Python: {sys.executable}")
    print(f"Version: {sys.version}")
    # Now try importing and starting Flask
    from flask import Flask
    print("Flask imported OK")
    from whatsapp_automation import ConfigService, ExcelService, AutomationEngine
    print("whatsapp_automation imported OK")
    import webview
    print("webview imported OK")
    print("ALL IMPORTS OK - checking app.py load...")
    # Try to load app module
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_test", os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py"))
    print(f"spec: {spec}")
    mod = importlib.util.module_from_spec(spec)
    print("Module created, about to exec...")
    # Don't actually exec the module as it will start the server
    print("TEST COMPLETE - all OK")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
finally:
    sys.stdout.flush()
