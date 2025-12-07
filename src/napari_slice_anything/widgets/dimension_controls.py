"""Dimension controls widget component."""

from typing import Optional, Tuple, List

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from napari.layers import Image


class DimensionSliceControl(QWidget):
    """A widget with text inputs for controlling slice bounds on one dimension."""

    def __init__(self, dim_index: int, dim_size: int, dim_name: str = "", parent=None):
        super().__init__(parent)
        self.dim_index = dim_index
        self.dim_size = dim_size

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.label = QLabel(dim_name or f"Dim {dim_index}")
        self.label.setMinimumWidth(80)
        self.label.setMaximumWidth(120)
        layout.addWidget(self.label)

        # Simple text inputs for direct value entry
        self.min_edit = QLineEdit()
        self.max_edit = QLineEdit()
        
        for edit in [self.min_edit, self.max_edit]:
            edit.setMaximumWidth(60)
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.textChanged.connect(self._validate_input)
        
        self.min_edit.setText("0")
        self.max_edit.setText(str(dim_size - 1))
        
        layout.addWidget(self.min_edit)
        layout.addWidget(QLabel("to"))
        layout.addWidget(self.max_edit)
        layout.addStretch()

        self.size_label = QLabel(f"[{dim_size}]")
        self.size_label.setMinimumWidth(70)
        self.size_label.setMaximumWidth(90)
        layout.addWidget(self.size_label)

    def _validate_input(self):
        """Validate text input and ensure valid ranges."""
        try:
            min_val = int(self.min_edit.text()) if self.min_edit.text() else 0
            max_val = int(self.max_edit.text()) if self.max_edit.text() else self.dim_size - 1
            
            # Clamp to valid range
            min_val = max(0, min(min_val, self.dim_size - 1))
            max_val = max(0, min(max_val, self.dim_size - 1))
            
            # Update display if values were clamped
            if min_val != int(self.min_edit.text()) if self.min_edit.text() else 0:
                self.min_edit.setText(str(min_val))
            if max_val != int(self.max_edit.text()) if self.max_edit.text() else self.dim_size - 1:
                self.max_edit.setText(str(max_val))
                
        except ValueError:
            # Invalid input, clear the field
            if self.sender() == self.min_edit:
                self.min_edit.setText("0")
            else:
                self.max_edit.setText(str(self.dim_size - 1))

    def get_slice(self) -> Tuple[int, int]:
        """Return the current (min, max) slice values as integers."""
        try:
            min_val = int(self.min_edit.text()) if self.min_edit.text() else 0
            max_val = int(self.max_edit.text()) if self.max_edit.text() else self.dim_size - 1
            
            # Ensure valid range
            min_val = max(0, min(min_val, self.dim_size - 1))
            max_val = max(0, min(max_val, self.dim_size - 1))
            
            return (min_val, max_val + 1)
        except ValueError:
            return (0, self.dim_size)

    def set_dim_info(self, dim_size: int, dim_name: str = ""):
        """Update dimension size and name."""
        self.dim_size = dim_size
        self.max_edit.setText(str(dim_size - 1))
        self.size_label.setText(f"[{dim_size}]")
        if dim_name:
            self.label.setText(dim_name)


class DimensionControls(QWidget):
    """Container widget for managing multiple dimension slice controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dim_controls: List[DimensionSliceControl] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.controls_layout = layout

    def clear_controls(self):
        """Remove all dimension controls."""
        for control in self._dim_controls:
            self.controls_layout.removeWidget(control)
            control.deleteLater()
        self._dim_controls.clear()

    def setup_controls(self, layer: Optional[Image]):
        """Set up dimension controls based on image shape."""
        self.clear_controls()

        if layer is None:
            return

        shape = layer.data.shape
        axis_names = getattr(layer, "axis_names", None)
        if axis_names is None or len(axis_names) != len(shape):
            axis_names = [f"Axis {i}" for i in range(len(shape))]

        for i, (size, name) in enumerate(zip(shape, axis_names)):
            control = DimensionSliceControl(i, size, str(name))
            self._dim_controls.append(control)
            self.controls_layout.addWidget(control)

    def get_all_slices(self) -> List[slice]:
        """Get slice objects for all dimensions based on current control values."""
        slices = []
        for control in self._dim_controls:
            start, stop = control.get_slice()
            slices.append(slice(start, stop))
        return slices

    def get_spatial_dimensions(self) -> List[DimensionSliceControl]:
        """Get dimension controls for spatial dimensions (size > 1)."""
        return [control for control in self._dim_controls if control.dim_size > 1]

    def reset_all(self):
        """Reset all dimension controls to full range."""
        for control in self._dim_controls:
            control.min_edit.setText("0")
            control.max_edit.setText(str(control.dim_size - 1))
