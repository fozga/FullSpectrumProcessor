from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PyQt5.QtCore import Qt, QRectF, QPointF, QRect
from PyQt5.QtGui import QPainter, QPixmap, QPen, QColor
from PyQt5.QtWidgets import QApplication

class ImageViewer(QGraphicsView):
    """
    A custom graphics view for displaying and interacting with images.

    This widget provides features such as:
      - Displaying images with zoom and fit-to-view capabilities.
      - Smooth rendering and antialiasing.
      - Drag-to-pan functionality.
      - Mouse wheel zoom with Ctrl modifier.
      - Automatic scene rect and transformation management.

    Attributes:
        zoom (float): Current zoom factor.
        fit_to_view (bool): Whether the image is fit to the view.
        scene (QGraphicsScene): The graphics scene containing the image.
        photo (QGraphicsPixmapItem): The pixmap item displaying the image.
    """
    def __init__(self, parent=None):
        """
        Initializes the ImageViewer with default settings.

        Args:
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)
        self.zoom = 1.0
        self.fit_to_view = False
        self.scene = QGraphicsScene(self)
        self.photo = self.scene.addPixmap(QPixmap())
        self.setScene(self.scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        # Crop-related state
        self._crop_mode = False
        self._crop_rect = None  # Current temporary crop rectangle
        self._saved_crop_rect = None  # Last confirmed crop rectangle
        self._crop_ratio = None
        self._crop_handle_size = 20
        self._dragging = False
        self._drag_start = None
        self._drag_handle = None
        self._original_crop_rect = None
        self._anchor_point = None
        self._fixed_edges = None
        self._min_crop_size = 50

    def toggle_view(self):
        """
        Toggles between fit-to-view and manual zoom modes.

        - If toggled on, fits the image to the view while preserving aspect ratio.
        - If toggled off, resets any zoom or transformation.
        """
        self.fit_to_view = not self.fit_to_view
        if self.fit_to_view:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
            self.zoom = 1.0
        else:
            self.resetTransform()
            self.zoom = 1.0

    def set_image(self, pixmap):
        """
        Sets the displayed image.

        Args:
            pixmap (QPixmap): The image to display.

        Behavior:
            - Sets the pixmap in the scene.
            - Fits the image to the view.
            - Resets the zoom factor.
        """
        self.photo.setPixmap(pixmap)
        self.fitInView(self.photo, Qt.KeepAspectRatio)
        self.zoom = 1.0

    def wheelEvent(self, event):
        """
        Handles mouse wheel events for zooming.

        - Holding Ctrl and using the wheel zooms in/out.
        - Exits fit-to-view mode on manual zoom.
        - Otherwise, passes the event to the base class.

        Args:
            event (QWheelEvent): The wheel event.
        """
        if event.modifiers() & Qt.ControlModifier:
            zoom_factor = 1.25
            if event.angleDelta().y() > 0:
                self.scale(zoom_factor, zoom_factor)
                self.zoom *= zoom_factor
                self.fit_to_view = False  # Exit fit-to-view on manual zoom
            else:
                self.scale(1/zoom_factor, 1/zoom_factor)
                self.zoom /= zoom_factor
                self.fit_to_view = False
            event.accept()
        else:
            super().wheelEvent(event)

    def resizeEvent(self, event):
        """
        Handles widget resize events.

        - If in fit-to-view mode, refits the image to the new view size.

        Args:
            event (QResizeEvent): The resize event.
        """
        if self.fit_to_view:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        super().resizeEvent(event)
            
    def mousePressEvent(self, event):
        """
        Handles mouse press events.

        - Enables scroll-hand drag mode on left mouse button press.

        Args:
            event (QMouseEvent): The mouse press event.
        """
        if self._crop_mode and event.button() == Qt.LeftButton:
            self._drag_handle = self.get_handle_at(event.pos())
            if self._drag_handle:
                self._dragging = True
                self._drag_start = self.mapToScene(event.pos())
                self._original_crop_rect = QRect(self._crop_rect)  # Store original rect
                self._anchor_point = self.get_anchor_point(self._drag_handle, self._crop_rect)
                # Store fixed edges for corner handles
                if self._drag_handle in ['top_left', 'top_right', 'bottom_left', 'bottom_right']:
                    rect = self._crop_rect
                    self._fixed_edges = {
                        'top': rect.top(),
                        'bottom': rect.bottom(),
                        'left': rect.left(),
                        'right': rect.right()
                    }
                else:
                    self._fixed_edges = None
                if self._drag_handle == 'move':
                    self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handles mouse release events.

        - Disables drag mode when the mouse is released.

        Args:
            event (QMouseEvent): The mouse release event.
        """
        if self._crop_mode and event.button() == Qt.LeftButton:
            if self._dragging:
                self._dragging = False
                self._drag_handle = None
                # Update cursor based on current position
                handle = self.get_handle_at(event.pos())
                self.update_cursor_for_handle(handle)
                event.accept()
                return
        self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._crop_mode:
            if self._dragging and self._crop_rect:
                current_pos = self.mapToScene(event.pos())
                if self._drag_handle == 'move':
                    delta = current_pos - self._drag_start
                    self._drag_start = current_pos
                    self._crop_rect.translate(int(delta.x()), int(delta.y()))
                else:
                    self.resize_crop_rect_from_anchor(self._drag_handle, self._anchor_point, current_pos, self._original_crop_rect)
                self.constrain_crop_rect()
                self.viewport().update()
                event.accept()
                return
            else:
                # Update cursor based on handle under mouse
                handle = self.get_handle_at(event.pos())
                self.update_cursor_for_handle(handle)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def enterEvent(self, event):
        if self._crop_mode:
            handle = self.get_handle_at(event.pos())
            self.update_cursor_for_handle(handle)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._crop_mode:
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def update_cursor_for_handle(self, handle):
        if self._dragging and self._drag_handle == 'move':
            self.setCursor(Qt.ClosedHandCursor)
        elif handle == 'move':
            self.setCursor(Qt.SizeAllCursor)  # Four arrows for center area
        elif handle in ['top_left', 'bottom_right']:
            self.setCursor(Qt.SizeFDiagCursor)  # Diagonal arrow for top-left/bottom-right
        elif handle in ['top_right', 'bottom_left']:
            self.setCursor(Qt.SizeBDiagCursor)  # Diagonal arrow for top-right/bottom-left
        elif handle in ['left', 'right']:
            self.setCursor(Qt.SizeHorCursor)  # Horizontal arrow for left/right
        elif handle in ['top', 'bottom']:
            self.setCursor(Qt.SizeVerCursor)  # Vertical arrow for top/bottom
        else:
            self.setCursor(Qt.ArrowCursor)
        # Force immediate cursor update
        QApplication.processEvents()

    def set_crop_mode(self, enabled):
        self._crop_mode = enabled
        if enabled:
            if self.photo.pixmap():
                if self._saved_crop_rect:
                    # Use last saved crop rectangle if available
                    self._crop_rect = QRect(self._saved_crop_rect)
                else:
                    # Initialize to 80% of image size, centered
                    img_width = self.photo.pixmap().width()
                    img_height = self.photo.pixmap().height()
                    rect_width = int(img_width * 0.8)
                    rect_height = int(img_height * 0.8)
                    x = (img_width - rect_width) // 2
                    y = (img_height - rect_height) // 2
                    self._crop_rect = QRect(x, y, rect_width, rect_height)
                
                if self._crop_ratio:
                    self.adjust_crop_rect_to_ratio()
            self.setCursor(Qt.ArrowCursor)
        else:
            # Discard temporary crop rectangle when exiting crop mode
            self._crop_rect = None
            self.setCursor(Qt.ArrowCursor)
        self.viewport().update()

    def confirm_crop(self):
        if self._crop_rect:
            self._saved_crop_rect = QRect(self._crop_rect)
        self.set_crop_mode(False)

    def cancel_crop(self):
        self._crop_rect = None
        self.set_crop_mode(False)

    def set_crop_rect(self, rect):
        self._crop_rect = rect
        self.viewport().update()

    def set_crop_ratio(self, ratio):
        if not self._crop_rect:
            self._crop_ratio = ratio
            return

        # Update the ratio
        self._crop_ratio = ratio
        
        # Adjust the current rectangle to the new ratio
        self.adjust_crop_rect_to_ratio()

    def adjust_crop_rect_to_ratio(self):
        if not self._crop_ratio or not self._crop_rect:
            return

        # Get current dimensions
        original_width = self._crop_rect.width()
        original_height = self._crop_rect.height()
        
        # Calculate new dimensions based on ratio
        w, h = self._crop_ratio
        target_ratio = w / h
        
        # First try to maintain width and adjust height
        new_width = original_width
        new_height = int(new_width / target_ratio)
        
        # If new height would exceed original height, maintain height instead
        if new_height > original_height:
            new_height = original_height
            new_width = int(new_height * target_ratio)
        
        # Create new rectangle maintaining the top-left corner position
        new_rect = QRect(
            self._crop_rect.left(),
            self._crop_rect.top(),
            new_width,
            new_height
        )
        
        # Ensure the new rectangle stays within image bounds
        bounds = self.photo.boundingRect()
        if new_rect.right() > bounds.right():
            new_rect.setRight(int(bounds.right()))
            new_rect.setWidth(int(new_rect.height() * target_ratio))
        if new_rect.bottom() > bounds.bottom():
            new_rect.setBottom(int(bounds.bottom()))
            new_rect.setHeight(int(new_rect.width() / target_ratio))
        
        self._crop_rect = new_rect
        self.viewport().update()

    def get_handle_at(self, pos):
        if not self._crop_rect:
            return None

        # Convert view coordinates to scene coordinates
        scene_pos = self.mapToScene(pos)
        rect = self._crop_rect
        handle_size = self._crop_handle_size

        # Define handle areas with larger hit regions
        handles = {
            'top_left': QRectF(rect.left() - handle_size, rect.top() - handle_size,
                             handle_size * 2, handle_size * 2),
            'top_right': QRectF(rect.right() - handle_size, rect.top() - handle_size,
                              handle_size * 2, handle_size * 2),
            'bottom_left': QRectF(rect.left() - handle_size, rect.bottom() - handle_size,
                                handle_size * 2, handle_size * 2),
            'bottom_right': QRectF(rect.right() - handle_size, rect.bottom() - handle_size,
                                 handle_size * 2, handle_size * 2),
            'top': QRectF(rect.left() + handle_size, rect.top() - handle_size,
                         rect.width() - handle_size * 2, handle_size * 2),
            'bottom': QRectF(rect.left() + handle_size, rect.bottom() - handle_size,
                            rect.width() - handle_size * 2, handle_size * 2),
            'left': QRectF(rect.left() - handle_size, rect.top() + handle_size,
                          handle_size * 2, rect.height() - handle_size * 2),
            'right': QRectF(rect.right() - handle_size, rect.top() + handle_size,
                           handle_size * 2, rect.height() - handle_size * 2)
        }

        # First check corners and edges
        for handle, handle_rect in handles.items():
            if handle_rect.contains(scene_pos):
                return handle

        # Then check if inside crop rect (for moving)
        if rect.contains(scene_pos.toPoint()):
            return 'move'

        return None

    def get_anchor_point(self, handle, rect):
        # Returns the fixed anchor point (QPoint) for a given handle and rect
        if handle == 'top_left':
            return rect.bottomRight()
        elif handle == 'top_right':
            return rect.bottomLeft()
        elif handle == 'bottom_left':
            return rect.topRight()
        elif handle == 'bottom_right':
            return rect.topLeft()
        elif handle == 'left':
            return rect.center() + (rect.right() - rect.left()) // 2 * QPointF(1, 0)
        elif handle == 'right':
            return rect.center() - (rect.right() - rect.left()) // 2 * QPointF(1, 0)
        elif handle == 'top':
            return rect.center() + (rect.bottom() - rect.top()) // 2 * QPointF(0, 1)
        elif handle == 'bottom':
            return rect.center() - (rect.bottom() - rect.top()) // 2 * QPointF(0, 1)
        else:
            return rect.center()

    def resize_crop_rect_from_anchor(self, handle, anchor, mouse_scene_pos, original_rect):
        bounds = self.photo.boundingRect()
        anchor = QPointF(anchor)
        mouse = QPointF(mouse_scene_pos)
        # Clamp mouse to image bounds
        mouse.setX(max(bounds.left(), min(bounds.right(), mouse.x())))
        mouse.setY(max(bounds.top(), min(bounds.bottom(), mouse.y())))
        # For corners, fix two opposite edges
        if handle in ['top_left', 'top_right', 'bottom_left', 'bottom_right'] and self._fixed_edges:
            fe = self._fixed_edges
            if handle == 'top_left':
                fixed_right = fe['right']
                fixed_bottom = fe['bottom']
                moving_x = mouse.x()
                moving_y = mouse.y()
                moving_x = min(moving_x, fixed_right - 10)
                moving_y = min(moving_y, fixed_bottom - 10)
                width = fixed_right - moving_x
                height = fixed_bottom - moving_y
                if self._crop_ratio:
                    w, h = self._crop_ratio
                    target_ratio = w / h
                    if width / target_ratio > height:
                        width = int(height * target_ratio)
                    else:
                        height = int(width / target_ratio)
                    moving_x = fixed_right - width
                    moving_y = fixed_bottom - height
                new_rect = QRect(int(moving_x), int(moving_y), int(fixed_right - moving_x), int(fixed_bottom - moving_y))
            elif handle == 'top_right':
                fixed_left = fe['left']
                fixed_bottom = fe['bottom']
                moving_x = mouse.x()
                moving_y = mouse.y()
                moving_x = max(moving_x, fixed_left + 10)
                moving_y = min(moving_y, fixed_bottom - 10)
                width = moving_x - fixed_left
                height = fixed_bottom - moving_y
                if self._crop_ratio:
                    w, h = self._crop_ratio
                    target_ratio = w / h
                    if width / target_ratio > height:
                        width = int(height * target_ratio)
                        moving_x = fixed_left + width
                    else:
                        height = int(width / target_ratio)
                        moving_y = fixed_bottom - height
                new_rect = QRect(int(fixed_left), int(moving_y), int(moving_x - fixed_left), int(fixed_bottom - moving_y))
            elif handle == 'bottom_left':
                fixed_right = fe['right']
                fixed_top = fe['top']
                moving_x = mouse.x()
                moving_y = mouse.y()
                moving_x = min(moving_x, fixed_right - 10)
                moving_y = max(moving_y, fixed_top + 10)
                width = fixed_right - moving_x
                height = moving_y - fixed_top
                if self._crop_ratio:
                    w, h = self._crop_ratio
                    target_ratio = w / h
                    if width / target_ratio > height:
                        width = int(height * target_ratio)
                        moving_x = fixed_right - width
                    else:
                        height = int(width / target_ratio)
                        moving_y = fixed_top + height
                new_rect = QRect(int(moving_x), int(fixed_top), int(fixed_right - moving_x), int(moving_y - fixed_top))
            elif handle == 'bottom_right':
                fixed_left = fe['left']
                fixed_top = fe['top']
                moving_x = mouse.x()
                moving_y = mouse.y()
                moving_x = max(moving_x, fixed_left + 10)
                moving_y = max(moving_y, fixed_top + 10)
                width = moving_x - fixed_left
                height = moving_y - fixed_top
                if self._crop_ratio:
                    w, h = self._crop_ratio
                    target_ratio = w / h
                    if width / target_ratio > height:
                        width = int(height * target_ratio)
                        moving_x = fixed_left + width
                    else:
                        height = int(width / target_ratio)
                        moving_y = fixed_top + height
                new_rect = QRect(int(fixed_left), int(fixed_top), int(moving_x - fixed_left), int(moving_y - fixed_top))
            # Clamp new_rect to image bounds
            new_rect = new_rect.intersected(QRect(int(bounds.left()), int(bounds.top()), int(bounds.width()), int(bounds.height())))
            if new_rect.width() < self._min_crop_size or new_rect.height() < self._min_crop_size:
                return  # Maintain minimum size
            self._crop_rect = new_rect
        elif handle in ['left', 'right', 'top', 'bottom']:
            rect = QRectF(original_rect)
            if self._crop_ratio:
                w, h = self._crop_ratio
                target_ratio = w / h
                if handle in ['left', 'right']:
                    if handle == 'left':
                        fixed_right = rect.right()
                        new_left = min(mouse.x(), fixed_right - 10)
                        width = fixed_right - new_left
                        height = int(round(width / target_ratio))
                        center_y = rect.center().y()
                        new_top = int(round(center_y - height / 2))
                        new_bottom = new_top + height
                        # Clamp to bounds
                        if new_left < bounds.left():
                            new_left = bounds.left()
                            width = fixed_right - new_left
                            height = int(round(width / target_ratio))
                            new_top = int(round(center_y - height / 2))
                            new_bottom = new_top + height
                        if new_top < bounds.top():
                            new_top = bounds.top()
                            height = rect.bottom() - new_top
                            width = int(round(height * target_ratio))
                            new_left = fixed_right - width
                            new_bottom = new_top + height
                        if new_bottom > bounds.bottom():
                            new_bottom = bounds.bottom()
                            height = new_bottom - new_top
                            width = int(round(height * target_ratio))
                            new_left = fixed_right - width
                        new_rect = QRect(int(new_left), int(new_top), int(width), int(height))
                    else:  # handle == 'right'
                        fixed_left = rect.left()
                        new_right = max(mouse.x(), fixed_left + 10)
                        width = new_right - fixed_left
                        height = int(round(width / target_ratio))
                        center_y = rect.center().y()
                        new_top = int(round(center_y - height / 2))
                        new_bottom = new_top + height
                        # Clamp to bounds
                        if new_right > bounds.right():
                            new_right = bounds.right()
                            width = new_right - fixed_left
                            height = int(round(width / target_ratio))
                            new_top = int(round(center_y - height / 2))
                            new_bottom = new_top + height
                        if new_top < bounds.top():
                            new_top = bounds.top()
                            height = rect.bottom() - new_top
                            width = int(round(height * target_ratio))
                            new_right = fixed_left + width
                            new_bottom = new_top + height
                        if new_bottom > bounds.bottom():
                            new_bottom = bounds.bottom()
                            height = new_bottom - new_top
                            width = int(round(height * target_ratio))
                            new_right = fixed_left + width
                        new_rect = QRect(int(fixed_left), int(new_top), int(width), int(height))
                else:
                    if handle == 'top':
                        fixed_bottom = rect.bottom()
                        new_top = min(mouse.y(), fixed_bottom - 10)
                        height = fixed_bottom - new_top
                        width = int(round(height * target_ratio))
                        center_x = rect.center().x()
                        new_left = int(round(center_x - width / 2))
                        new_right = new_left + width
                        # Clamp to bounds
                        if new_top < bounds.top():
                            new_top = bounds.top()
                            height = fixed_bottom - new_top
                            width = int(round(height * target_ratio))
                            new_left = int(round(center_x - width / 2))
                            new_right = new_left + width
                        if new_left < bounds.left():
                            new_left = bounds.left()
                            width = new_right - new_left
                            height = int(round(width / target_ratio))
                            new_top = fixed_bottom - height
                        if new_right > bounds.right():
                            new_right = bounds.right()
                            width = new_right - new_left
                            height = int(round(width / target_ratio))
                            new_top = fixed_bottom - height
                        new_rect = QRect(int(new_left), int(new_top), int(width), int(height))
                    else:  # handle == 'bottom'
                        fixed_top = rect.top()
                        new_bottom = max(mouse.y(), fixed_top + 10)
                        height = new_bottom - fixed_top
                        width = int(round(height * target_ratio))
                        center_x = rect.center().x()
                        new_left = int(round(center_x - width / 2))
                        new_right = new_left + width
                        # Clamp to bounds
                        if new_bottom > bounds.bottom():
                            new_bottom = bounds.bottom()
                            height = new_bottom - fixed_top
                            width = int(round(height * target_ratio))
                            new_left = int(round(center_x - width / 2))
                            new_right = new_left + width
                        if new_left < bounds.left():
                            new_left = bounds.left()
                            width = new_right - new_left
                            height = int(round(width / target_ratio))
                            new_bottom = fixed_top + height
                        if new_right > bounds.right():
                            new_right = bounds.right()
                            width = new_right - new_left
                            height = int(round(width / target_ratio))
                            new_bottom = fixed_top + height
                        new_rect = QRect(int(new_left), int(fixed_top), int(width), int(height))
                if new_rect.width() < self._min_crop_size or new_rect.height() < self._min_crop_size:
                    return  # Maintain minimum size
                self._crop_rect = new_rect
            else:
                # Free aspect: allow edge dragging
                left = rect.left()
                right = rect.right()
                top = rect.top()
                bottom = rect.bottom()
                if handle == 'left':
                    new_left = min(mouse.x(), right - 10)
                    left = new_left
                elif handle == 'right':
                    new_right = max(mouse.x(), left + 10)
                    right = new_right
                elif handle == 'top':
                    new_top = min(mouse.y(), bottom - 10)
                    top = new_top
                elif handle == 'bottom':
                    new_bottom = max(mouse.y(), top + 10)
                    bottom = new_bottom
                # Clamp to image bounds
                left = max(bounds.left(), left)
                right = min(bounds.right(), right)
                top = max(bounds.top(), top)
                bottom = min(bounds.bottom(), bottom)
                width = int(right - left)
                height = int(bottom - top)
                new_rect = QRect(int(left), int(top), int(width), int(height))
                if new_rect.width() < self._min_crop_size or new_rect.height() < self._min_crop_size:
                    return  # Maintain minimum size
                self._crop_rect = new_rect

    def constrain_crop_rect(self):
        if not self._crop_rect or not self.photo:
            return

        # Get image bounds
        bounds = self.photo.boundingRect()
        min_x = int(bounds.left())
        max_x = int(bounds.right())
        min_y = int(bounds.top())
        max_y = int(bounds.bottom())

        # Store original dimensions
        original_width = self._crop_rect.width()
        original_height = self._crop_rect.height()

        # Create a new rectangle with constrained coordinates
        new_rect = QRect(
            int(max(min_x, min(max_x - original_width, self._crop_rect.left()))),
            int(max(min_y, min(max_y - original_height, self._crop_rect.top()))),
            original_width,
            original_height
        )

        # Update the crop rectangle
        self._crop_rect = new_rect

        # If we have a fixed ratio, maintain it
        if self._crop_ratio:
            self.adjust_crop_rect_to_ratio()

    def drawForeground(self, painter, rect):
        if not self._crop_mode or not self._crop_rect:
            return

        # Draw semi-transparent overlay
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setBrush(QColor(0, 0, 0, 128))
        painter.setPen(Qt.NoPen)
        
        # Draw overlay only outside the crop rectangle
        scene_rect = self.sceneRect()
        painter.drawRect(QRectF(scene_rect.left(), scene_rect.top(), 
                              self._crop_rect.left() - scene_rect.left(), scene_rect.height()))
        painter.drawRect(QRectF(self._crop_rect.right(), scene_rect.top(),
                              scene_rect.right() - self._crop_rect.right(), scene_rect.height()))
        painter.drawRect(QRectF(self._crop_rect.left(), scene_rect.top(),
                              self._crop_rect.width(), self._crop_rect.top() - scene_rect.top()))
        painter.drawRect(QRectF(self._crop_rect.left(), self._crop_rect.bottom(),
                              self._crop_rect.width(), scene_rect.bottom() - self._crop_rect.bottom()))

        # Draw crop rectangle
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.setBrush(Qt.NoBrush)
        pen = QPen(Qt.white, 2, Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(self._crop_rect)

        # Draw handles
        handle_size = 8
        pen = QPen(Qt.white, 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(Qt.white)

        # Draw corner handles
        corners = [
            (self._crop_rect.left(), self._crop_rect.top(), 'top_left'),
            (self._crop_rect.right(), self._crop_rect.top(), 'top_right'),
            (self._crop_rect.left(), self._crop_rect.bottom(), 'bottom_left'),
            (self._crop_rect.right(), self._crop_rect.bottom(), 'bottom_right')
        ]
        for x, y, handle in corners:
            handle_rect = QRectF(float(x) - handle_size/2, float(y) - handle_size/2, 
                               float(handle_size), float(handle_size))
            painter.drawRect(handle_rect)

        # Draw edge handles
        edges = [
            (self._crop_rect.left() + self._crop_rect.width()/2, self._crop_rect.top(), 'top'),
            (self._crop_rect.right(), self._crop_rect.top() + self._crop_rect.height()/2, 'right'),
            (self._crop_rect.left() + self._crop_rect.width()/2, self._crop_rect.bottom(), 'bottom'),
            (self._crop_rect.left(), self._crop_rect.top() + self._crop_rect.height()/2, 'left')
        ]
        for x, y, handle in edges:
            handle_rect = QRectF(float(x) - handle_size/2, float(y) - handle_size/2, 
                               float(handle_size), float(handle_size))
            painter.drawRect(handle_rect)
