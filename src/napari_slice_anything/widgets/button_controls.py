"""Button controls widget component."""

from qtpy.QtWidgets import QHBoxLayout, QPushButton, QWidget


class ButtonControls(QWidget):
    """Widget containing action buttons for slicing operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        self.apply_btn = QPushButton("Apply Slice")
        self.apply_btn.setEnabled(False)
        layout.addWidget(self.apply_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setEnabled(False)
        layout.addWidget(self.reset_btn)
        
        self.draw_box_btn = QPushButton("Apply Crop from Shape")
        self.draw_box_btn.setEnabled(False)
        self.draw_box_btn.setToolTip("Apply crop area from selected shape in a shapes layer")
        layout.addWidget(self.draw_box_btn)

        layout.addStretch()

    def set_apply_enabled(self, enabled: bool):
        """Enable or disable the apply button."""
        self.apply_btn.setEnabled(enabled)

    def set_reset_enabled(self, enabled: bool):
        """Enable or disable the reset button."""
        self.reset_btn.setEnabled(enabled)

    def set_crop_enabled(self, enabled: bool):
        """Enable or disable the crop from shape button."""
        self.draw_box_btn.setEnabled(enabled)
