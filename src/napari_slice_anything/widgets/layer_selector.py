"""Layer selection widget component."""

from typing import Optional

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel

import napari
from napari.layers import Image


class LayerSelector(QGroupBox):
    """Widget for selecting image layers from napari viewer."""

    def __init__(self, napari_viewer: napari.Viewer, parent=None):
        super().__init__("Layer Selection", parent)
        self.viewer = napari_viewer
        self._current_layer: Optional[Image] = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.layer_combo = QComboBox()
        self.layer_combo.setPlaceholderText("Select an image layer...")
        layout.addRow("Image Layer:", self.layer_combo)

        self.shape_label = QLabel("No layer selected")
        layout.addRow("Shape:", self.shape_label)

        self._update_layer_combo()
        
        # Connect signals after UI is set up
        self.connect_signals()

    def _update_layer_combo(self, event=None):
        """Update the layer combo box with available image layers."""
        current_text = self.layer_combo.currentText()
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()

        for layer in self.viewer.layers:
            if isinstance(layer, Image):
                self.layer_combo.addItem(layer.name, layer)

        if current_text:
            idx = self.layer_combo.findText(current_text)
            if idx >= 0:
                self.layer_combo.setCurrentIndex(idx)

        self.layer_combo.blockSignals(False)

        if self.layer_combo.count() > 0 and self.layer_combo.currentIndex() == -1:
            self.layer_combo.setCurrentIndex(0)

    def connect_signals(self):
        """Connect signals for layer changes."""
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        self.viewer.layers.events.inserted.connect(self._update_layer_combo)
        self.viewer.layers.events.removed.connect(self._update_layer_combo)

    def _on_layer_changed(self, index: int):
        """Handle layer selection change."""
        if index < 0:
            self._current_layer = None
            self.shape_label.setText("No layer selected")
            return

        self._current_layer = self.layer_combo.itemData(index)
        if self._current_layer is not None:
            shape = self._current_layer.data.shape
            self.shape_label.setText(str(shape))

    def get_current_layer(self) -> Optional[Image]:
        """Get the currently selected layer."""
        return self._current_layer

    def is_layer_selected(self) -> bool:
        """Check if a layer is currently selected."""
        return self._current_layer is not None
