import os
import sys
import threading
import time
import urllib.request
import webview
import uvicorn

# Configure paths - handle PyInstaller one-file mode
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    ROOT_DIR = sys._MEIPASS
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

# Ensure Python can find the app module
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Important: switch current working directory to backend so that .env and paths resolve correctly
if getattr(sys, 'frozen', False):
    # TRUE PORTABLE MODE: Save the DB directly next to the .exe on the pendrive
    DATA_DIR = os.path.dirname(sys.executable)
    os.chdir(DATA_DIR)
else:
    os.chdir(BACKEND_DIR)

# Import app at the top level so PyInstaller hooks discover fastapi and all dependencies!
try:
    from app.main import app
except ImportError as e:
    print(f"[AlphaHunter] Warning: Failed to import app: {e}")
    app = None

def run_backend():
    print("[AlphaHunter] Starting internal backend server...")
    
    # Run uvicorn programmatically in this thread
        
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")

def wait_for_server(url, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url)
            return True
        except Exception:
            time.sleep(0.5)
    return False

if __name__ == "__main__":
    # Freeze support for Windows multi-processing (uvicorn uses multiprocessing)
    import multiprocessing
    import traceback
    multiprocessing.freeze_support()
    
    try:
        # 1. Start the FastAPI backend in a background thread
        t = threading.Thread(target=run_backend, daemon=True)
        t.start()
        
        # 2. Wait for the server to be ready
        print("[AlphaHunter] Waiting for backend to initialize...")
        if not wait_for_server("http://127.0.0.1:8001/api/health"):
            print("[AlphaHunter] Failed to connect to the backend server in time.")
            sys.exit(1)
            
        print("[AlphaHunter] Backend is ready. Launching Desktop UI...")
        
        # 3. Create a native desktop window using pywebview (uses Edge WebView2 on Windows)
        window = webview.create_window(
            title='AlphaHunter - AI Trading Intelligence',
            url='http://127.0.0.1:8001',
            width=1400,
            height=900,
            min_size=(1024, 768),
            frameless=False
        )
        
        # 4. Start the application event loop
        webview.start(debug=False)
    except Exception as e:
        crash_log_path = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), "crash.log")
        if getattr(sys, 'frozen', False):
             crash_log_path = os.path.join(os.getenv('APPDATA'), "AlphaHunter", "crash.log")
        with open(crash_log_path, "w") as f:
            f.write(traceback.format_exc())
        print(f"CRASHED! Wrote log to {crash_log_path}")
        time.sleep(10)
