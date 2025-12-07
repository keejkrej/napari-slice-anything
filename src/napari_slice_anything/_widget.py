"""Main widget for slicing multidimensional image stacks."""

from typing import Optional

import numpy as np
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import napari
from napari.layers import Image, Shapes


class DimensionSliceControl(QWidget):
    """A widget with text inputs for controlling slice bounds on one dimension."""

    def __init__(self, dim_index: int, dim_size: int, dim_name: str = "", parent=None):
        super().__init__(parent)
        self.dim_index = dim_index
        self.dim_size = dim_size

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)  # Increased margins to prevent clipping

        self.label = QLabel(dim_name or f"Dim {dim_index}")
        self.label.setMinimumWidth(80)
        self.label.setMaximumWidth(120)  # Increased to prevent clipping
        layout.addWidget(self.label)

        # Simple text inputs for direct value entry
        self.min_edit = QLineEdit()
        self.max_edit = QLineEdit()
        
        for edit in [self.min_edit, self.max_edit]:
            edit.setMaximumWidth(60)
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.setStyleSheet("""
                QLineEdit {
                    border: 1px solid gray;
                    padding: 2px;
                    background: white;
                    font-weight: bold;
                    font-size: 10px;
                }
            """)
            edit.textChanged.connect(self._validate_input)
        
        self.min_edit.setText("0")
        self.max_edit.setText(str(dim_size - 1))
        
        layout.addWidget(self.min_edit)
        layout.addWidget(QLabel("to"))
        layout.addWidget(self.max_edit)
        layout.addStretch()

        self.size_label = QLabel(f"[{dim_size}]")
        self.size_label.setMinimumWidth(70)
        self.size_label.setMaximumWidth(90)  # Increased to prevent clipping
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
        
    def get_slice(self) -> tuple[int, int]:
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

    def get_slice(self) -> tuple[int, int]:
        """Return the current (min, max) slice values as integers."""
        val = self.range_slider.value()
        return (int(val[0]), int(val[1]) + 1)

    def set_dim_info(self, dim_size: int, dim_name: str = ""):
        """Update dimension size and name."""
        self.dim_size = dim_size
        self.range_slider.data_range = (0, dim_size - 1)
        self.range_slider.set_values((0, dim_size - 1))
        self.size_label.setText(f"[{dim_size}]")
        if dim_name:
            self.label.setText(dim_name)


class SliceAnythingWidget(QWidget):
    """A napari widget for slicing multidimensional image stacks using range sliders."""

    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self._current_layer: Optional[Image] = None
        self._dim_controls: list[DimensionSliceControl] = []

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layer_group = QGroupBox("Layer Selection")
        layer_layout = QFormLayout(layer_group)

        self.layer_combo = QComboBox()
        self.layer_combo.setPlaceholderText("Select an image layer...")
        layer_layout.addRow("Image Layer:", self.layer_combo)

        self.shape_label = QLabel("No layer selected")
        layer_layout.addRow("Shape:", self.shape_label)

        layout.addWidget(layer_group)

        self.dims_group = QGroupBox("Dimension Slicing")
        self.dims_layout = QVBoxLayout(self.dims_group)
        self.dims_layout.addWidget(QLabel("Select an image layer to configure slicing"))
        layout.addWidget(self.dims_group)

        button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Slice")
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setEnabled(False)
        button_layout.addWidget(self.reset_btn)
        
        self.draw_box_btn = QPushButton("Apply Crop from Shape")
        self.draw_box_btn.setEnabled(False)
        self.draw_box_btn.setToolTip("Apply crop area from selected shape in a shapes layer")
        button_layout.addWidget(self.draw_box_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        self._update_layer_combo()

    def _connect_signals(self):
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        self.apply_btn.clicked.connect(self._apply_slice)
        self.reset_btn.clicked.connect(self._reset_sliders)
        self.draw_box_btn.clicked.connect(self._apply_crop_from_shape)

        self.viewer.layers.events.inserted.connect(self._update_layer_combo)
        self.viewer.layers.events.removed.connect(self._update_layer_combo)

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
            self._on_layer_changed(0)

    def _on_layer_changed(self, index: int):
        """Handle layer selection change."""
        if index < 0:
            self._current_layer = None
            self._clear_dim_controls()
            self.shape_label.setText("No layer selected")
            self.apply_btn.setEnabled(False)
            self.reset_btn.setEnabled(False)
            self.draw_box_btn.setEnabled(False)
            return

        self._current_layer = self.layer_combo.itemData(index)
        if self._current_layer is None:
            return

        shape = self._current_layer.data.shape
        self.shape_label.setText(str(shape))
        self._setup_dim_controls(shape)
        self.apply_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.draw_box_btn.setEnabled(True)  # Enable if there's any shapes layer

    def _clear_dim_controls(self):
        """Remove all dimension controls."""
        for control in self._dim_controls:
            self.dims_layout.removeWidget(control)
            control.deleteLater()
        self._dim_controls.clear()

        for i in reversed(range(self.dims_layout.count())):
            item = self.dims_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

    def _setup_dim_controls(self, shape: tuple):
        """Set up dimension controls based on image shape."""
        self._clear_dim_controls()

        axis_names = getattr(self._current_layer, "axis_names", None)
        if axis_names is None or len(axis_names) != len(shape):
            axis_names = [f"Axis {i}" for i in range(len(shape))]

        for i, (size, name) in enumerate(zip(shape, axis_names)):
            control = DimensionSliceControl(i, size, str(name))
            self._dim_controls.append(control)
            self.dims_layout.addWidget(control)

    def _apply_slice(self):
        """Apply the current slice configuration to create a new layer."""
        if self._current_layer is None:
            return

        slices = []
        for control in self._dim_controls:
            start, stop = control.get_slice()
            slices.append(slice(start, stop))

        sliced_data = self._current_layer.data[tuple(slices)]

        if sliced_data.size == 0:
            return

        new_name = f"{self._current_layer.name}_sliced"
        existing_names = [l.name for l in self.viewer.layers]
        counter = 1
        base_name = new_name
        while new_name in existing_names:
            new_name = f"{base_name}_{counter}"
            counter += 1

        # Create a layer that napari's save system can recognize
        try:
            # Copy display properties from original layer
            layer_kwargs = {
                'name': new_name,
                'data': sliced_data,
                'rgb': False,
            }
            
            # Copy visual properties that might affect saving
            if hasattr(self._current_layer, 'contrast_limits'):
                try:
                    layer_kwargs['contrast_limits'] = self._current_layer.contrast_limits
                except:
                    pass
            
            if hasattr(self._current_layer, 'gamma'):
                try:
                    layer_kwargs['gamma'] = self._current_layer.gamma
                except:
                    pass
                    
            if hasattr(self._current_layer, 'interpolation'):
                try:
                    layer_kwargs['interpolation'] = self._current_layer.interpolation
                except:
                    pass
            
            # Create the layer first
            new_layer = self.viewer.add_image(**layer_kwargs)
            
            # Now set up proper source metadata for napari's save system
            try:
                # Create a proper source object that mimics a file-loaded layer
                from napari.layers._source import Source
                
                # For sliced layers, we let the user choose the filename in the save dialog
                # So we don't set a hardcoded path here
                new_layer._source = Source(
                    path=None,  # Let user choose filename in save dialog
                    reader_plugin='napari',
                    plugin='napari-slice-anything'
                )
                
                # Add metadata that helps with saving
                new_layer.metadata.update({
                    'sliced_by': 'napari-slice-anything',
                    'original_layer': self._current_layer.name,
                    'original_shape': list(self._current_layer.data.shape),
                    'sliced_shape': list(sliced_data.shape),
                    'slice_bounds': [(c.get_slice()[0], c.get_slice()[1]) for c in self._dim_controls]
                })
                
                # Ensure the layer has properties that make it saveable
                # Set some attributes that the npe2 system checks for
                new_layer._type_string = 'image'  # Explicitly set type
                
            except Exception as e:
                print(f"Warning: Could not set up complete source metadata: {e}")
                # Fallback: at least ensure basic metadata
                new_layer.metadata.update({
                    'sliced_by': 'napari-slice-anything',
                    'original_layer': self._current_layer.name
                })
                
        except Exception as e:
            print(f"Warning: Could not create layer with full properties: {e}")
            # Minimal fallback
            new_layer = self.viewer.add_image(
                sliced_data,
                name=new_name,
                rgb=False,
                metadata={'sliced_by': 'napari-slice-anything'}
            )

    def _apply_crop_from_shape(self):
        """Apply crop area from selected shape in a shapes layer."""
        # Find the currently selected shapes layer
        shapes_layer = None
        for layer in self.viewer.layers:
            if isinstance(layer, Shapes) and len(layer.data) > 0:
                # Check if any shapes are selected
                if hasattr(layer, 'selected_data') and layer.selected_data:
                    shapes_layer = layer
                    break
        
        if shapes_layer is None:
            print("No selected shapes found. Please select a shape in a shapes layer.")
            return
            
        try:
            # Get the first selected shape's data
            selected_indices = list(shapes_layer.selected_data)
            if not selected_indices:
                print("No shape selected. Please select a shape in the shapes layer.")
                return
                
            shape_index = selected_indices[0]
            shape_data = shapes_layer.data[shape_index]
            
            # Extract bounding box coordinates
            if len(shape_data) >= 4:  # Rectangle or polygon
                coords = np.array(shape_data)
                min_x = int(np.min(coords[:, 0]))
                max_x = int(np.max(coords[:, 0]))
                min_y = int(np.min(coords[:, 1]))
                max_y = int(np.max(coords[:, 1]))
                
                # Debug: Show raw coordinates first
                print(f"Raw shape coordinates: {coords}")
                print(f"Raw min/max: X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]")
                
                # Try to convert to data coordinates if the shapes layer has transformation
                try:
                    if hasattr(shapes_layer, 'data_to_world'):
                        # Convert shape coordinates to data coordinates
                        world_coords = np.column_stack([coords[:, 0], coords[:, 1]])
                        data_coords = shapes_layer.data_to_world(world_coords)
                        min_x = int(np.min(data_coords[:, 0]))
                        max_x = int(np.max(data_coords[:, 0]))
                        min_y = int(np.min(data_coords[:, 1]))
                        max_y = int(np.max(data_coords[:, 1]))
                        print(f"Data coordinates: X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]")
                except Exception as e:
                    print(f"Coordinate conversion failed: {e}, using raw coordinates")
                
                # Also try to account for current slice position
                try:
                    current_step = list(self.viewer.dims.current_step)
                    if len(current_step) >= 2:
                        # The shape might be relative to current slice position
                        # Try both raw and offset coordinates
                        offset_x_min = min_x + current_step[-1] if len(current_step) > 0 else min_x
                        offset_x_max = max_x + current_step[-1] if len(current_step) > 0 else max_x
                        offset_y_min = min_y + current_step[-2] if len(current_step) > 1 else min_y
                        offset_y_max = max_y + current_step[-2] if len(current_step) > 1 else max_y
                        
                        print(f"Offset coordinates: X=[{offset_x_min}, {offset_x_max}], Y=[{offset_y_min}, {offset_y_max}]")
                        
                        # Use the offset coordinates if they seem more reasonable
                        if abs(offset_x_max - offset_x_min) > abs(max_x - min_x):
                            min_x, max_x = offset_x_min, offset_x_max
                            min_y, max_y = offset_y_min, offset_y_max
                            print("Using offset coordinates")
                        
                except Exception as e:
                    print(f"Offset calculation failed: {e}")
                
                # Ensure coordinates are within bounds of the current layer
                if self._current_layer is not None:
                    shape = self._current_layer.data.shape
                    # Clamp to valid range
                    min_x = max(0, min(min_x, shape[-1] - 1))
                    max_x = max(0, min(max_x, shape[-1] - 1))
                    min_y = max(0, min(min_y, shape[-2] - 1))
                    max_y = max(0, min(max_y, shape[-2] - 1))
                    
                # Find spatial dimension controls (last 2 dimensions with size > 1)
                spatial_controls = []
                for control in self._dim_controls:
                    if control.dim_size > 1:
                        spatial_controls.append(control)
                
                # Apply to the last 2 spatial dimensions (usually X, Y)
                if len(spatial_controls) >= 2:
                    # Apply to X dimension (second to last)
                    x_control = spatial_controls[-2]
                    x_control.min_edit.setText(str(min_x))
                    x_control.max_edit.setText(str(max_x))
                    
                    # Apply to Y dimension (last)
                    y_control = spatial_controls[-1]
                    y_control.min_edit.setText(str(min_y))
                    y_control.max_edit.setText(str(max_y))
                    
                    print(f"Crop applied from shape: X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]")
                    print(f"Updated sliders: {x_control.label.text()} and {y_control.label.text()}")
                else:
                    print("Could not find 2 spatial dimensions to apply crop")
            else:
                print("Selected shape doesn't have enough vertices for a bounding box")
                
        except Exception as e:
            print(f"Error applying crop from shape: {e}")

    def _reset_sliders(self):
        """Reset all sliders to full range."""
        if self._current_layer is None:
            return

        shape = self._current_layer.data.shape
        for control, size in zip(self._dim_controls, shape):
            control.min_edit.setText("0")
            control.max_edit.setText(str(size - 1))
