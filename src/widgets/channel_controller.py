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

# pylint: disable=too-few-public-methods

"""
Channel controller widget for manipulating individual RGB channels.
Provides sliders for brightness, contrast, and intensity adjustments,
along with numeric input fields and channel preview.
"""

from typing import Union

import cv2
import numpy as np
from PyQt5.QtCore import QRect, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class ChannelController(QGroupBox):
    """
    Widget for controlling a single RGB channel.

    Provides:
    - Load button for importing channel image
    - Sliders for brightness, contrast, and intensity adjustments
    - Text inputs for precise value entry
    - Preview label showing the processed channel

    Emits:
    - value_changed: Signal when any adjustment value changes
    """

    # Custom signal to notify when any adjustment value changes
    value_changed = pyqtSignal()

    def __init__(self, channel_name: str, color: Qt.GlobalColor, parent: Union[QWidget, None] = None) -> None:
        """
        Initialize a channel controller with sliders and preview label.

        Args:
            channel_name (str): Name of the channel (red, green, blue)
            color (Qt.GlobalColor): Color for visual identification
            parent: Parent widget
        """
        super().__init__(parent)
        self.setTitle(f"{channel_name.capitalize()} channel")
        self.setStyleSheet("QGroupBox { font-size: 12pt; font-weight: bold;}")

        self.channel_name = channel_name
        self.color = color
        self.processed_image = None

        # Set up the UI components
        self._init_ui()

    def _init_ui(self) -> None:
        """Set up the controller UI layout with widgets."""
        main_layout = QVBoxLayout(self)

        # Create a horizontal layout for preview and load button
        preview_section = QHBoxLayout()

        # Map standard RGB channel names to abbreviated spectrum names
        channel_abbrev = {"red": "IR", "green": "VIS", "blue": "UV"}.get(self.channel_name, self.channel_name[:3])

        # Button to load the channel image - now placed to the right of preview
        self.btn_load = QPushButton(f"Load\n{channel_abbrev}")
        self.btn_load.setFixedSize(50, 120)  # Match height of preview
        preview_section.addWidget(self.btn_load)

        # Preview area for the processed image
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(160, 120)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid gray;")
        preview_section.addWidget(self.preview_label)

        # Add the preview section to the main layout
        main_layout.addLayout(preview_section)

        # Create sliders and their text input fields
        self.sliders = {}
        self.text_inputs = {}

        # Define slider parameters
        slider_configs: dict[str, dict[str, Union[int, str]]] = {
            "brightness": {"min": -100, "max": 100, "default": 0, "label": "Brightness"},
            "contrast": {"min": -100, "max": 100, "default": 0, "label": "Contrast"},
            "intensity": {"min": 0, "max": 100, "default": 100, "label": "Intensity"},
        }

        # Create a grid layout for the adjustment controls
        adjustments_layout = QGridLayout()
        adjustments_layout.setColumnStretch(1, 2)  # Make the slider column expandable
        # adjustments_layout.setColumnMinimumWidth(1, 100)  # Reduced width for sliders
        adjustments_layout.setHorizontalSpacing(5)  # Add horizontal spacing between elements
        adjustments_layout.setVerticalSpacing(5)  # Add some vertical spacing

        # Create each slider with label and numeric input in a grid
        row = 0
        for name, config in slider_configs.items():
            # Add the label in first column
            label = QLabel(f"{config['label']}:")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            adjustments_layout.addWidget(label, row, 0)

            # Create slider
            slider = QSlider(Qt.Horizontal)

            # Ensure numeric values are used for slider operations
            assert isinstance(config["min"], int)
            slider.setMinimum(config["min"])
            assert isinstance(config["max"], int)
            slider.setMaximum(config["max"])
            assert isinstance(config["default"], int)
            slider.setValue(config["default"])
            slider.setTracking(True)
            self.sliders[name] = slider
            adjustments_layout.addWidget(slider, row, 1)

            # Create and set up text input field
            text_input = QLineEdit()
            text_input.setText(str(config["default"]))
            text_input.setFixedWidth(35)
            text_input.setAlignment(Qt.AlignRight)
            self.text_inputs[name] = text_input
            adjustments_layout.addWidget(text_input, row, 2)

            # Connect slider to text input and value_changed signal
            slider.valueChanged.connect(
                lambda value, input_field=text_input: self._update_text_from_slider(value, input_field)
            )

            # Connect text input to slider
            text_input.editingFinished.connect(
                lambda slider=slider, input_field=text_input: self._update_slider_from_text(slider, input_field)
            )

            row += 1

        # Add the grid layout to the main layout with some spacing
        main_layout.addLayout(adjustments_layout)

        # Set initial preview to placeholder
        self._create_placeholder_preview()

        # Set a fixed width for the controller
        self.setFixedWidth(240)

    def _update_text_from_slider(self, value: int, text_input: QLineEdit) -> None:
        """
        Update text input field when slider value changes.

        Args:
            value (int): New slider value
            text_input (QLineEdit): Text field to update
        """
        # Block signals to prevent recursive updates
        text_input.blockSignals(True)
        text_input.setText(str(value))
        text_input.blockSignals(False)

        # Emit value changed signal
        self.value_changed.emit()

    def _update_slider_from_text(self, slider: QSlider, text_input: QLineEdit) -> None:
        """
        Update slider position when text input changes.

        Args:
            slider (QSlider): Slider to update
            text_input (QLineEdit): Text field containing new value
        """
        try:
            # Get text value and validate it's a number in the valid range
            new_value = int(text_input.text())
            min_val = slider.minimum()
            max_val = slider.maximum()

            if new_value < min_val:
                new_value = min_val
            elif new_value > max_val:
                new_value = max_val

            # Update text field with clamped value
            text_input.setText(str(new_value))

            # Update slider (this will also trigger value_changed)
            slider.blockSignals(True)
            slider.setValue(new_value)
            slider.blockSignals(False)

            # Emit value changed signal
            self.value_changed.emit()

        except ValueError:
            # If not a valid number, restore to current slider value
            text_input.setText(str(slider.value()))

    def _create_placeholder_preview(self) -> None:
        """Create an empty placeholder preview."""
        placeholder = np.zeros((120, 160), dtype=np.uint8)
        # Add a light gray value to make it visible
        placeholder.fill(30)
        self._set_preview(placeholder)

    def update_preview(self) -> None:
        """Update the preview label with the current processed image."""
        if self.processed_image is not None:
            self._set_preview(self.processed_image)
        else:
            self._create_placeholder_preview()

    def _set_preview(self, img: np.ndarray) -> None:
        """
        Set the preview image in the label.

        Args:
            img (np.ndarray): Grayscale image to display
        """
        # Create a copy of the image to avoid potential reference issues
        preview_img = img.copy()

        # Get dimensions from parent if possible to handle cropping
        parent = self.parent()
        while parent:
            if hasattr(parent, "viewer") and hasattr(parent.viewer, "get_saved_crop_rect"):
                saved_crop_rect = parent.viewer.get_saved_crop_rect()
                if saved_crop_rect and not getattr(parent, "crop_mode", False):
                    # Apply crop on-the-fly for previews too
                    h, w = preview_img.shape[:2]

                    valid_rect = QRect(0, 0, w, h).intersected(saved_crop_rect)
                    if valid_rect.isValid() and valid_rect.width() > 0 and valid_rect.height() > 0:
                        preview_img = preview_img[
                            valid_rect.top() : valid_rect.bottom() + 1, valid_rect.left() : valid_rect.right() + 1
                        ].copy()
                break
            parent = parent.parent()

        # Resize while preserving aspect ratio
        h, w = preview_img.shape[:2]
        aspect = w / h

        if aspect > 160 / 120:  # Width-constrained
            new_w = 160
            new_h = int(new_w / aspect)
        else:  # Height-constrained
            new_h = 120
            new_w = int(new_h * aspect)

        preview = cv2.resize(preview_img, (new_w, new_h), interpolation=cv2.INTER_AREA)  # pylint: disable=E1101

        # Convert to QPixmap and set in label
        q_img = QImage(preview.data, preview.shape[1], preview.shape[0], preview.strides[0], QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_img)
        self.preview_label.setPixmap(pixmap)
