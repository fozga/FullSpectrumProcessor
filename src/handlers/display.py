"""
Display handlers for updating the main image view and channel previews in the application.
"""

import numpy as np
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QPixmap

from core.image_processing import combine_channels, convert_to_qimage


def update_main_display(main_window):
    """
    Updates the main image display area based on the current application state.

    Depending on whether the user wants to view the combined RGB image or a single channel,
    this function delegates to the appropriate display function. It also ensures that the
    scene rectangle in the viewer matches the displayed image size.

    Args:
        main_window: Reference to the main application window containing image data and UI state.
    """
    if main_window.show_combined:
        show_combined_image(main_window)
    else:
        show_single_channel_image(main_window)

    if main_window.viewer.photo.pixmap():
        pixmap = main_window.viewer.photo.pixmap()
        main_window.viewer.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))


def show_combined_image(main_window):
    """
    Displays the combined RGB image in the main viewer.

    Combines the three processed channels using their respective intensity slider values,
    converts the result to a QImage, and sets it in the viewer.

    Args:
        main_window: Reference to the main application window.
    """
    if any(img is None for img in main_window.processed):
        return
    intensities = [ctrl.slider_intensity.value() for ctrl in main_window.controllers]
    combined = combine_channels(main_window.processed, intensities)
    q_img = convert_to_qimage(combined)
    main_window.viewer.set_image(QPixmap.fromImage(q_img))


def show_single_channel_image(main_window):
    """
    Displays a single selected channel as a grayscale image in the main viewer.

    The selected channel is duplicated across RGB for display purposes, converted to QImage,
    and shown in the viewer.

    Args:
        main_window: Reference to the main application window.
    """
    img = main_window.processed[main_window.current_channel]
    if img is not None:
        rgb_img = np.stack([img] * 3, axis=-1)
        q_img = convert_to_qimage(rgb_img)
        main_window.viewer.set_image(QPixmap.fromImage(q_img))
