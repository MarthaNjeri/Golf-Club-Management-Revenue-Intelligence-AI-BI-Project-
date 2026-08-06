import subprocess
import sys
import time

def main():
    print("🚀 Starting FairwayIQ Engine & PWA Sync Services...\n")
    
    # 1. Start FastAPI Background Sync Engine on Port 8000
    api_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "api_router:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])
    
    # Give FastAPI a moment to initialize
    time.sleep(1.5)
    
    # 2. Start Streamlit Application on Port 8501
    streamlit_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "app.py", 
        "--server.port", "8501"
    ])

    print("\n✅ Both FairwayIQ services are running!")
    print("   • Streamlit UI: http://localhost:8501")
    print("   • Sync API:     http://localhost:8000/docs\n")
    print("Press Ctrl+C in this terminal to stop both services.\n")

    try:
        api_process.wait()
        streamlit_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down FairwayIQ services cleanly...")
        api_process.terminate()
        streamlit_process.terminate()
        api_process.wait()
        streamlit_process.wait()
        print("Done!")

if __name__ == "__main__":
    main()