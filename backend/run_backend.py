import uvicorn
import multiprocessing
from app.main import app
import os
import sys

if __name__ == '__main__':
    multiprocessing.freeze_support()
    # Route to scraper service if requested (PyInstaller subprocess workaround)
    if len(sys.argv) > 1 and "scraper_service.py" in sys.argv[1]:
        from app.collectors.nse.scraper_service import run
        run()
        sys.exit(0)

    # When bundled by PyInstaller, set CWD to the executable's directory
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path)
    
    # Run the FastAPI app on a fixed local port
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
