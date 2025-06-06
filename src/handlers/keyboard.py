"""
Keyboard event handler utilities for the RGB Channel Processor application.

This module provides functions to handle keyboard shortcuts for channel switching and display mode toggling in the main window.

Cross-references:
    - handlers.display.update_main_display: Refreshes the main display.
    - main_window.MainWindow: Main application window.
"""

from PyQt5.QtCore import Qt
from handlers.display import update_main_display

def handle_key_press(main_window, event):
    """
    Handles keyboard shortcuts for channel switching and display modes.

    Args:
        main_window (QMainWindow): Reference to the main application window.
        event (QKeyEvent): QKeyEvent from PyQt5's key press handler.

    Returns:
        bool: True if the key was handled, False otherwise (allows event propagation).

    Key Bindings:
        - 1: Show Red channel (index 0)
        - 2: Show Green channel (index 1)
        - 3: Show Blue channel (index 2)
        - A: Show combined RGB view

    Behavior:
        - Updates display state in main_window
        - Calls update_main_display() to refresh the UI
        - Accepts the event if handled to prevent further propagation

    Cross-references:
        - update_main_display
        - main_window.MainWindow
    """
    if event.key() == Qt.Key_1:
        main_window.show_combined = False
        main_window.current_channel = 0
        update_main_display(main_window)
        event.accept()
        return True
    elif event.key() == Qt.Key_2:
        main_window.show_combined = False
        main_window.current_channel = 1
        update_main_display(main_window)
        event.accept()
        return True
    elif event.key() == Qt.Key_3:
        main_window.show_combined = False
        main_window.current_channel = 2
        update_main_display(main_window)
        event.accept()
        return True
    elif event.key() == Qt.Key_A:
        main_window.show_combined = True
        update_main_display(main_window)
        event.accept()
        return True
    return False
