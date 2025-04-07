# Used for building an executable that can be run on any machine.
# Read more on pyInstaller: https://pyinstaller.org/
# This is just temp until docker is set up

# IMPORTANT: Install new .exe file using this command:  pyinstaller py_installer.spec
# If the .exe cannot start, ensure the py_installer.spec has the following line:
# hiddenimports=['passlib.handlers.bcrypt']
# And then reinstall with the abovementioned command
from app.main import app

if __name__ == '__main__':
    import uvicorn
    try:
        uvicorn.run(app, host="127.0.0.1", port=8000)
    except Exception as e:
        print(f"An error occurred: {e}")
    input("Press Enter to exit...")