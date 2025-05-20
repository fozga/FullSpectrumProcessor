from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QToolBar, QAction, QComboBox, QPushButton)
from PyQt5.QtCore import Qt, QRect
from widgets.image_viewer import ImageViewer
from widgets.channel_controller import ChannelController
from handlers.keyboard import handle_key_press
from handlers.channels import load_channel, adjust_channel, update_channel_preview, show_single_channel
from handlers.display import update_main_display
from core.image_processing import combine_channels

class MainWindow(QMainWindow):
    """
    Main application window for the RGB Channel Processor.

    This window manages the overall GUI layout, holds the state of loaded and processed images,
    and connects user interactions (buttons, sliders, keyboard) to the processing logic.
    """
    
    def __init__(self):
        """
        Initialize the main window, set up the title, geometry, internal state,
        and construct the user interface.
        """
        super().__init__()
        self.setWindowTitle("RGB Channel Processor")
        self.setGeometry(100, 100, 1200, 800)

        # State: original, aligned, and processed images for R, G, B channels
        self.original_images = [None, None, None]
        self.aligned = [None, None, None]
        self.processed = [None, None, None]
        # Display state
        self.show_combined = True  # If True, show combined RGB; else show single channel
        self.current_channel = 0   # Index of the currently selected channel
        
        # Crop-related state
        self.crop_mode = False
        self.crop_rect = None
        self.crop_ratio = None
        
        self.init_ui()

    def init_ui(self):
        """
        Build the main UI layout: image viewer and channel controllers.

        - Adds an ImageViewer widget for displaying images.
        - Adds three ChannelController widgets (R, G, B) with sliders and load buttons.
        - Connects controller signals to appropriate handler functions.
        """
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

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
        left_panel.addWidget(self.crop_mode_btn)
        left_panel.addWidget(self.crop_controls_widget)
        self.viewer = ImageViewer()
        left_panel.addWidget(self.viewer, 70)

        main_layout.addLayout(left_panel, 70)

        # Right panel with channel controllers
        right_panel = QVBoxLayout()
        self.controllers = [
            ChannelController("red", Qt.red),
            ChannelController("green", Qt.green),
            ChannelController("blue", Qt.blue)
        ]

        for idx, controller in enumerate(self.controllers):
            # Connect load button and sliders to handlers
            controller.btn_load.clicked.connect(lambda _, i=idx: load_channel(self, i))
            controller.slider_brightness.valueChanged.connect(lambda v, i=idx: adjust_channel(self, i))
            controller.slider_contrast.valueChanged.connect(lambda v, i=idx: adjust_channel(self, i))
            controller.slider_intensity.valueChanged.connect(lambda v, i=idx: update_main_display(self))
            controller.preview_label.mousePressEvent = (lambda event, i=idx: show_single_channel(self, i))

            right_panel.addWidget(controller)
        right_panel.addStretch()
        main_layout.addLayout(right_panel, 30)

        self.setCentralWidget(main_widget)

    def toggle_crop_mode(self):
        if self.crop_mode:
            return
        if not any(img is not None for img in self.processed):
            return  # Add error message in UI
        self.crop_mode = True
        self.crop_mode_btn.setVisible(False)
        self.crop_controls_widget.setVisible(True)
        # Use last saved crop rectangle if available
        if hasattr(self.viewer, '_saved_crop_rect') and self.viewer._saved_crop_rect:
            self.crop_rect = QRect(self.viewer._saved_crop_rect)
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
                if self.crop_ratio:
                    self.crop_rect = self._get_aspect_crop_rect(self.crop_rect, self.crop_ratio)
        self.viewer.set_crop_mode(self.crop_mode)
        if self.crop_rect:
            self.viewer.set_crop_rect(self.crop_rect)
        update_main_display(self)

    def cancel_crop(self):
        self.crop_mode = False
        self.crop_mode_btn.setVisible(True)
        self.crop_controls_widget.setVisible(False)
        if hasattr(self.viewer, '_saved_crop_rect') and self.viewer._saved_crop_rect:
            self.crop_rect = QRect(self.viewer._saved_crop_rect)
            self.viewer.set_crop_rect(self.crop_rect)
        else:
            self.crop_rect = None
        self.viewer.set_crop_mode(False)
        update_main_display(self)

    def set_crop_ratio(self, index):
        self.crop_ratio = self.crop_ratio_combo.currentData()
        # Always get the current rectangle from the viewer
        current_rect = self.viewer._crop_rect if self.viewer._crop_rect else self.crop_rect
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

    def _get_aspect_crop_rect(self, rect, ratio):
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

    def apply_crop(self):
        crop_rect = self.viewer._crop_rect if self.viewer._crop_rect else self.crop_rect
        if not crop_rect or not any(img is not None for img in self.processed):
            return
        self.viewer._saved_crop_rect = crop_rect
        self.crop_mode = False
        self.crop_mode_btn.setVisible(True)
        self.crop_controls_widget.setVisible(False)
        self.viewer.set_crop_mode(False)
        update_main_display(self)

    def keyPressEvent(self, event):
        """
        Handle key press events for channel switching and display mode.

        Delegates to handle_key_press; falls back to default if not handled.
        """
        if self.crop_mode:
            if event.key() == Qt.Key_Escape:
                self.cancel_crop()
            elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self.apply_crop()
            # Do not allow toggling crop mode with 'C' while in crop mode
            else:
                super().keyPressEvent(event)
        else:
            if event.key() == Qt.Key_C:
                self.toggle_crop_mode()
            elif not handle_key_press(self, event):
                super().keyPressEvent(event)
