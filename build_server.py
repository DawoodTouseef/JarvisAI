import PyInstaller.__main__
import os

# Build the Python server executable
PyInstaller.__main__.run([
    '--onefile',
    '--windowed',  # No console window
    '--name=jarvis_server',
    '--add-data=server;server',  # Include server directory
    'server/main.py'
])