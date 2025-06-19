# Copyright (C) 2025 fozga
#
# This file is part of FullSpectrumProcessor.
#
# FullSpectrumProcessor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FullSpectrumProcessor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with FullSpectrumProcessor.  If not, see <https://www.gnu.org/licenses/>.

"""
Main application window and UI layout for the RGB Channel Processor.
Handles state management, user interactions, and connects UI components to processing logic.
"""

from typing import Callable, Union

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QKeyEvent, QMouseEvent
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStatusBar, QVBoxLayout, QWidget

from .handlers.channels import adjust_channel, load_channel, show_single_channel, update_channel_preview
from .handlers.display import show_combined_image, show_single_channel_image, update_main_display
from .handlers.image_saving import save_image_with_dialog
from .handlers.keyboard import handle_key_press
from .widgets.channel_controller import ChannelController
from .widgets.image_viewer import ImageViewer
from .widgets.status_bar import StatusBarHandler


class MainWindow(QMainWindow):  # pylint: disable=too-many-instance-attributes
    """
        Main application window for the RGB Channel Processor.

        This window manages the overall GUI layout, holds the state of loaded and processed images,
        and connects user interactions (buttons, sliders, keyboard) to the processing logic.

        Related components:
            - ImageViewer (widgets.image_viewer): Displays the main image.
            - ChannelController (widgets.channel_controller): Controls for each RGB channel.
    - StatusBarHandler (widgets.status_bar): Manages the status bar.
            - handlers.channels: Functions for loading and adjusting channels.
            - handlers.display: Functions for updating the main display.
            - handlers.keyboard: Keyboard shortcut handling.
    """

    def __init__(self) -> None:
        """
        Initialize the main window, set up the title, geometry, internal state,
        and construct the user interface.

        Args:
            self (MainWindow): The instance of the main window.

        Returns:
            None
        """
        super().__init__()
        self.setWindowTitle("RGB Channel Processor")
        self.setGeometry(100, 100, 1200, 800)

        # State: original, aligned, and processed images for R, G, B channels
        self.original_images = [None, None, None]
        self.aligned = [None, None, None]
        self.processed = [None, None, None]
        # Add original RGB images storage
        self.original_rgb_images = [None, None, None]
        self.aligned_rgb = [None, None, None]

        # Display state
        self.show_combined = True  # If True, show combined RGB; else show single channel
        self.current_channel = 0  # Index of the currently selected channel

        # Crop-related state
        self.crop_mode = False
        self.crop_rect: Union[QRect, None] = None
        self.crop_ratio: Union[tuple[int, int], None] = None

        self.init_ui()

        # Update the mode based on initial state
        self._update_mode_from_state()

    def init_ui(self) -> None:  # pylint: disable=too-many-statements
        """
        Build the main UI layout: image viewer and channel controllers.

        Args:
            self (MainWindow): The instance of the main window.

        Returns:
            None

        - Adds an ImageViewer widget for displaying images.
        - Adds three ChannelController widgets (R, G, B) with sliders and load buttons.
        - Connects controller signals to appropriate handler functions.

        Cross-references:
            - ImageViewer
            - ChannelController
            - handlers.channels.load_channel, adjust_channel, update_channel_preview, show_single_channel
        """
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        # Add status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self.status_handler = StatusBarHandler(status_bar)

        # Add save button
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_images)
        self.save_btn.setEnabled(False)  # Initially disabled

        # Add crop mode button (QPushButton)
        self.crop_mode_btn = QPushButton("Crop")
        self.crop_mode_btn.clicked.connect(self.toggle_crop_mode)

        # Crop controls widget (already present)
        self.crop_ratio_combo = QComboBox()
        self.crop_ratio_combo.addItem("Free", None)
        self.crop_ratio_combo.addItem("16:9", (16, 9))
        self.crop_ratio_combo.addItem("3:2", (3, 2))
        self.crop_ratio_combo.addItem("4:3", (4, 3))
        self.crop_ratio_combo.addItem("5:4", (5, 4))
        self.crop_ratio_combo.addItem("1:1", (1, 1))
        self.crop_ratio_combo.addItem("4:5", (4, 5))
        self.crop_ratio_combo.addItem("3:4", (3, 4))
        self.crop_ratio_combo.addItem("2:3", (2, 3))
        self.crop_ratio_combo.addItem("9:16", (9, 16))
        self.crop_ratio_combo.currentIndexChanged.connect(self.set_crop_ratio)

        self.crop_controls_widget = QWidget()
        crop_controls_layout = QHBoxLayout(self.crop_controls_widget)
        crop_controls_layout.setContentsMargins(0, 0, 0, 0)
        crop_controls_layout.addWidget(self.crop_ratio_combo)
        self.accept_crop_btn = QPushButton("Accept Crop")
        self.accept_crop_btn.clicked.connect(self.apply_crop)
        crop_controls_layout.addWidget(self.accept_crop_btn)
        self.cancel_crop_btn = QPushButton("Cancel Crop")
        self.cancel_crop_btn.clicked.connect(self.cancel_crop)
        crop_controls_layout.addWidget(self.cancel_crop_btn)
        self.crop_controls_widget.setVisible(False)

        # Main vertical layout for left side (crop button + crop controls + image viewer)
        left_panel = QVBoxLayout()

        # Create a horizontal layout for the buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.crop_mode_btn)

        # Add the buttons layout to the left panel instead of just the crop button
        left_panel.addLayout(buttons_layout)
        left_panel.addWidget(self.crop_controls_widget)
        self.viewer = ImageViewer()
        left_panel.addWidget(self.viewer, 70)

        main_layout.addLayout(left_panel, 70)

        # Right panel with channel controllers
        right_panel = QVBoxLayout()
        self.controllers = [
            ChannelController("red", Qt.GlobalColor.red),
            ChannelController("green", Qt.GlobalColor.green),
            ChannelController("blue", Qt.GlobalColor.blue),
        ]

        for idx, controller in enumerate(self.controllers):
            # Connect load button and sliders to handlers
            controller.btn_load.clicked.connect(lambda _, i=idx: load_channel(self, i))

            # Connect controller value changes to adjust channel (handles both slider and text input)
            controller.value_changed.connect(lambda i=idx: adjust_channel(self, i))

            # Connect intensity directly to display update
            controller.sliders["intensity"].valueChanged.connect(lambda _: update_main_display(self))

            # Fix the mousePressEvent assignment with properly typed functions
            # Pass controller as an argument to avoid cell-var-from-loop issue
            def create_click_handler(index: int, ctrl: ChannelController = controller) -> Callable[[QMouseEvent], None]:
                """
                Creates a click handler function for channel preview labels.

                This factory function generates a click handler that shows a single channel
                when its preview label is clicked, while maintaining the original behavior
                of the QLabel's mousePressEvent.

                Parameters
                ----------
                index : int
                    The index of the channel to display when clicked.
                ctrl : ChannelController, optional
                    The channel controller instance to use. Defaults to the global controller.

                Returns
                -------
                Callable[[QMouseEvent], None]
                    A function that handles mouse press events on channel preview labels.
                """

                def click_handler(event: QMouseEvent) -> None:
                    """
                    Handle mouse click events on the channel preview label.

                    This function shows a single channel when the preview label is clicked and then
                    passes the event to the original mousePressEvent method to maintain expected behavior.

                    Parameters
                    ----------
                    event : QMouseEvent
                        The mouse event that triggered this handler.

                    Returns
                    -------
                    None
                    """
                    self.status_handler.set_message(
                        f"Viewing {ctrl.channel_name.capitalize()} channel", self.status_handler.MEDIUM_TIMEOUT
                    )
                    show_single_channel(self, index)
                    # Call the original method to maintain expected behavior
                    QLabel.mousePressEvent(ctrl.preview_label, event)

                return click_handler

            # Instead of directly assigning to mousePressEvent, connect to a custom event filter
            # or subclass QLabel - for now, we'll keep the assignment but add a type ignore comment
            controller.preview_label.mousePressEvent = create_click_handler(idx)  # type: ignore

            right_panel.addWidget(controller)
        right_panel.addStretch()
        main_layout.addLayout(right_panel, 30)

        self.setCentralWidget(main_widget)

        # After connecting all signals for loading/adjusting channels, update save button state
        self.update_save_button_state()

    def _update_mode_from_state(self) -> None:
        """
        Updates the mode indicator based on the current application state.

        Args:
            self (MainWindow): The instance of the main window.

        Returns:
            None
        """
        loaded_channels = sum(1 for img in self.original_images if img is not None)
        self.status_handler.update_mode_from_state(loaded_channels, self.crop_mode)

    def toggle_crop_mode(self) -> None:
        """
        Toggles the crop mode in the application.

        Args:
            self (MainWindow): The instance of the main window.

        Returns:
            None

        - Enables crop mode if currently disabled.
        - Displays crop controls and initializes the crop rectangle.
        - Uses the last saved crop rectangle if available.

        Cross-references:
            - ImageViewer.set_crop_mode
            - update_main_display
        """
        if self.crop_mode:
            return
        if not any(img is not None for img in self.processed):
            return  # Add error message in UI
        self.crop_mode = True
        self.crop_mode_btn.setVisible(False)
        self.crop_controls_widget.setVisible(True)
        # Use last saved crop rectangle if available
        saved_crop_rect = self.viewer.get_saved_crop_rect() if self.viewer else None
        if saved_crop_rect:
            self.crop_rect = QRect(saved_crop_rect)
        else:
            if any(img is not None for img in self.processed):
                for img in self.processed:
                    if img is not None:
                        img_w, img_h = img.shape[1], img.shape[0]
                        rect_w = int(img_w * 0.8)
                        rect_h = int(img_h * 0.8)
                        x = (img_w - rect_w) // 2
                        y = (img_h - rect_h) // 2
                        self.crop_rect = QRect(x, y, rect_w, rect_h)
                        break
                if self.crop_ratio and self.crop_rect is not None:
                    self.crop_rect = self._get_aspect_crop_rect(self.crop_rect, self.crop_ratio)
        self.viewer.set_crop_mode(self.crop_mode)
        if self.crop_rect:
            self.viewer.set_crop_rect(self.crop_rect)
        update_main_display(self)

        # Update mode indicator and status message
        self._update_mode_from_state()
        self.status_handler.set_message("Crop mode activated - Select region to crop", self.status_handler.NO_TIMEOUT)

    def cancel_crop(self) -> None:
        """
        Cancels the current crop operation.

        Args:
            self (MainWindow): The instance of the main window.

        Returns:
            None

        - Exits crop mode without applying changes.
        - Restores the last saved crop rectangle if available.

        Cross-references:
            - ImageViewer.set_crop_mode
            - update_main_display
        """
        self.crop_mode = False
        self.crop_mode_btn.setVisible(True)
        self.crop_controls_widget.setVisible(False)
        saved_crop_rect = self.viewer.get_saved_crop_rect() if self.viewer else None
        if saved_crop_rect:
            self.crop_rect = QRect(saved_crop_rect)
            self.viewer.set_crop_rect(self.crop_rect)
        else:
            self.crop_rect = None
        self.viewer.set_crop_mode(False)
        update_main_display(self)

        # Update mode indicator and status message
        self._update_mode_from_state()
        self.status_handler.set_message("Crop operation cancelled", self.status_handler.MEDIUM_TIMEOUT)

    def set_crop_ratio(self) -> None:
        """
        Sets the aspect ratio for the crop rectangle.

        Args:
            self (MainWindow): The instance of the main window.
            index (int): The index of the selected aspect ratio in the combo box.

        Returns:
            None

        - Adjusts the crop rectangle to maintain the selected aspect ratio.
        - Updates the viewer to reflect the new ratio.

        Cross-references:
            - ImageViewer.set_crop_ratio
            - update_main_display
        """
        self.crop_ratio = self.crop_ratio_combo.currentData()
        # Always get the current rectangle from the viewer
        current_rect = self.viewer.get_crop_rect() if self.viewer else self.crop_rect
        if current_rect and self.crop_ratio:
            new_rect = self._get_aspect_crop_rect(current_rect, self.crop_ratio)
            self.crop_rect = new_rect
            self.viewer.set_crop_ratio(self.crop_ratio)
            self.viewer.set_crop_rect(new_rect)
            # Keep viewer._crop_rect and self.crop_rect in sync
        elif current_rect:
            # Free mode
            self.viewer.set_crop_ratio(None)
            self.viewer.set_crop_rect(current_rect)
            self.crop_rect = current_rect
        update_main_display(self)

    def _get_aspect_crop_rect(self, rect: QRect, ratio: tuple[int, int]) -> QRect:
        """
        Returns the largest rectangle with the given aspect ratio that fits within the given rect,
        centered at the same point as the original rect.

        Args:
            self (MainWindow): The instance of the main window.
            rect (QRect): The original rectangle.
            ratio (tuple): The desired aspect ratio as (width, height).

        Returns:
            QRect: The adjusted rectangle.

        Cross-references:
            - set_crop_ratio
        """
        if not rect or not ratio:
            return rect
        orig_w = rect.width()
        orig_h = rect.height()
        center = rect.center()
        w, h = ratio
        target_ratio = w / h
        # Try to maintain width first
        new_w = orig_w
        new_h = int(new_w / target_ratio)
        if new_h > orig_h:
            new_h = orig_h
            new_w = int(new_h * target_ratio)
        # Center the new rect
        new_left = center.x() - new_w // 2
        new_top = center.y() - new_h // 2
        return QRect(new_left, new_top, new_w, new_h)

    def apply_crop(self) -> None:
        """
        Applies the current crop rectangle to the processed images.

        Args:
            self (MainWindow): The instance of the main window.

        Returns:
            None

        - Saves the crop rectangle for future use.
        - Exits crop mode and updates the main display.

        Cross-references:
            - ImageViewer._crop_rect, _saved_crop_rect
            - update_main_display
        """
        crop_rect = self.viewer.get_crop_rect() if self.viewer else self.crop_rect
        if not crop_rect or not any(img is not None for img in self.processed):
            return

        crop_rect = self.viewer.get_crop_rect()
        saved_rect = QRect(crop_rect) if crop_rect is not None else None
        if saved_rect is None:
            return

        # Make sure rectangle is valid and within bounds
        for i in range(3):
            if self.processed[i] is not None:
                img = self.processed[i]
                if img is not None:  # Double-check to satisfy type checker
                    img_height, img_width = img.shape[:2]
                    valid_rect = QRect(0, 0, img_width, img_height).intersected(saved_rect)
                    saved_rect = valid_rect
                    break

        if not saved_rect.isValid() or saved_rect.width() <= 0 or saved_rect.height() <= 0:
            return

        # Apply crop to the image in the viewer's scene (visual only)
        self.viewer.confirm_crop()

        # Store the crop rectangle for on-the-fly cropping during display
        # Don't modify the underlying images - this is the key change!
        self.viewer.set_saved_crop_rect(saved_rect)

        # Update all channel previews
        for i in range(3):
            update_channel_preview(self, i)

        # Reset crop mode and UI
        self.crop_mode = False
        self.crop_mode_btn.setVisible(True)
        self.crop_controls_widget.setVisible(False)
        self.viewer.set_crop_mode(False)

        # Update save button state after crop
        self.update_save_button_state()

        # Update mode indicator and status message
        self._update_mode_from_state()
        self.status_handler.set_message("Crop applied successfully", self.status_handler.MEDIUM_TIMEOUT)

        # Force a full display update
        if self.show_combined:
            show_combined_image(self)
        else:
            show_single_channel_image(self)

    def save_images(self) -> None:
        """
        Handle save button click by opening save dialog and saving images.

        Args:
            self (MainWindow): The instance of the main window.

        Returns:
            None
        """
        # Set mode to Saving before starting operation
        self.status_handler.update_mode_from_state(3, False, True)

        success, msg = save_image_with_dialog(self)

        # Restore appropriate mode after saving
        self._update_mode_from_state()

        if success:
            self.status_handler.set_message("Image saved successfully")
        else:
            self.status_handler.set_message(msg)

    def update_save_button_state(self) -> None:
        """
        Update the enabled state of the save button based on image availability.

        Args:
            self (MainWindow): The instance of the main window.

        Returns:
            None
        """
        # Enable save button if at least one channel image is available
        has_images = any(img is not None for img in self.aligned)
        self.save_btn.setEnabled(has_images)

        # Update mode indicator based on loaded channels
        self._update_mode_from_state()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # pylint: disable=C0103
        """
        Handle key press events for channel switching and display mode.

        Args:
            self (MainWindow): The instance of the main window.
            event (QKeyEvent): The key press event.

        Returns:
            None

        Delegates to handle_key_press; falls back to default if not handled.

        Cross-references:
            - handlers.keyboard.handle_key_press
            - toggle_crop_mode
            - cancel_crop
            - apply_crop
        """
        if self.crop_mode:
            if event.key() == Qt.Key.Key_Escape:
                self.cancel_crop()
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.apply_crop()
            # Do not allow toggling crop mode with 'C' while in crop mode
            else:
                super().keyPressEvent(event)
        else:
            if event.key() == Qt.Key.Key_C:
                self.toggle_crop_mode()
            elif not handle_key_press(self, event):
                super().keyPressEvent(event)
