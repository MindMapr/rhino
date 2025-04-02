# Used for building an executable that can be run on any machine.
# Read more on pyInstaller: https://pyinstaller.org/
# This is just temp until docker is set up
from app.main import app

if __name__ == '__main__':
    import uvicorn
    try:
        uvicorn.run(app, host="127.0.0.1", port=8000)
    except Exception as e:
        print(f"An error occurred: {e}")
    input("Press Enter to exit...")