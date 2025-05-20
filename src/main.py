"""
Main entry point for the RGB Channel Processor application.

This script initializes the Qt application, creates the main window,
and starts the event loop for the GUI.

Usage:
    python main.py

Modules:
    sys: Provides access to command-line arguments and system exit.
    PyQt5.QtWidgets.QApplication: Manages the Qt application event loop.
    main_window.MainWindow: Main window class for the application.
"""

import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow

def main():
    """
    Initialize and run the RGB Channel Processor application.

    This function creates a QApplication instance, instantiates and displays the main window,
    and starts the Qt event loop. The application will exit when the main window is closed.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
    

# TODO  Implement async processing
# TODO  Add status bar and feedback
# TODO  Add type/dimension checks in processing methods