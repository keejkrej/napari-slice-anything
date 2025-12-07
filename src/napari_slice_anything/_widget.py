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
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from napari._qt.widgets.qt_range_slider import QHRangeSlider

import napari
from napari.layers import Image, Shapes
from napari.layers.shapes._shapes_utils import create_box


class DimensionSliceControl(QWidget):
    """A widget with a range slider for controlling slice bounds on one dimension."""

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

        # Use napari's built-in QHRangeSlider for proper integer display
        self.range_slider = QHRangeSlider(
            initial_values=(0, dim_size - 1), 
            data_range=(0, dim_size - 1)
        )
        
        layout.addWidget(self.range_slider, stretch=1)

        self.size_label = QLabel(f"[{dim_size}]")
        self.size_label.setMinimumWidth(70)
        self.size_label.setMaximumWidth(90)  # Increased to prevent clipping
        layout.addWidget(self.size_label)

    def get_slice(self) -> tuple[int, int]:
        """Return the current (min, max) slice values as integers."""
        val = self.range_slider.values
        return (int(val[0]), int(val[1]) + 1)

    def set_dim_info(self, dim_size: int, dim_name: str = ""):
        """Update dimension size and name."""
        self.dim_size = dim_size
        self.range_slider.data_range = (0, dim_size - 1)
        self.range_slider.set_values((0, dim_size - 1))
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
        self._drawing_crop_box = False
        self._crop_box_layer: Optional[Shapes] = None
        self._drawing_start_pos = None
        self._current_crop_rect = None

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
        
        self.draw_box_btn = QPushButton("Draw Crop Box")
        self.draw_box_btn.setEnabled(False)
        self.draw_box_btn.setToolTip("Draw a rectangle on the image to define crop area")
        button_layout.addWidget(self.draw_box_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        self._update_layer_combo()

    def _connect_signals(self):
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        self.apply_btn.clicked.connect(self._apply_slice)
        self.reset_btn.clicked.connect(self._reset_sliders)
        self.draw_box_btn.clicked.connect(self._toggle_draw_box)

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
        self.draw_box_btn.setEnabled(True)

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

    def _reset_sliders(self):
        """Reset all sliders to full range."""
        if self._current_layer is None:
            return

        shape = self._current_layer.data.shape
        for control, size in zip(self._dim_controls, shape):
            control.range_slider.set_values((0, size - 1))

    def _toggle_draw_box(self):
        """Toggle crop box drawing mode."""
        if not self._drawing_crop_box:
            self._start_crop_box_drawing()
        else:
            self._stop_crop_box_drawing()

    def _start_crop_box_drawing(self):
        """Start crop box drawing mode."""
        self._drawing_crop_box = True
        self.draw_box_btn.setText("Finish Crop Box")
        self.draw_box_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        
        # Create a shapes layer for the crop box if it doesn't exist
        if self._crop_box_layer is None or self._crop_box_layer not in self.viewer.layers:
            self._crop_box_layer = self.viewer.add_shapes(
                name="Crop Box",
                face_color=[0, 255, 0, 0.1],  # Semi-transparent green
                edge_color=[0, 255, 0, 1],    # Solid green edges
                edge_width=2,
                ndim=2  # 2D rectangles
            )
        
        # Connect mouse event handlers
        self.viewer.canvas.events.mouse_press.connect(self._on_mouse_press)
        self.viewer.canvas.events.mouse_drag.connect(self._on_mouse_drag)
        self.viewer.canvas.events.mouse_release.connect(self._on_mouse_release)

    def _stop_crop_box_drawing(self):
        """Stop crop box drawing mode."""
        self._drawing_crop_box = False
        self.draw_box_btn.setText("Draw Crop Box")
        self.draw_box_btn.setStyleSheet("")  # Reset to default style
        
        # Remove event handlers
        try:
            self.viewer.canvas.events.mouse_press.disconnect(self._on_mouse_press)
            self.viewer.canvas.events.mouse_drag.disconnect(self._on_mouse_drag)
            self.viewer.canvas.events.mouse_release.disconnect(self._on_mouse_release)
        except:
            pass  # Event handlers might not be connected
        
        # Apply the crop box to sliders if we have a valid crop rectangle
        if self._current_crop_rect is not None:
            self._apply_crop_box_to_sliders(self._current_crop_rect)
        else:
            # Clear crop box if no valid rectangle
            if self._crop_box_layer:
                self._crop_box_layer.data = []
        
        # Reset drawing state
        self._drawing_start_pos = None
        self._current_crop_rect = None

    def _on_mouse_press(self, event):
        """Handle mouse press to start drawing crop box."""
        if not self._drawing_crop_box or not event.button == 0:  # Left click only
            return
            
        if self._current_layer is None:
            return
            
        pos = event.position
        if pos is None:
            return
            
        try:
            # Get current displayed dimensions and slice position
            current_step = list(self.viewer.dims.current_step)
            shape = self._current_layer.data.shape
            
            # Simple coordinate extraction for 2D view
            # We assume the current displayed 2D slice
            x_pos = int(pos[0]) if len(pos) > 0 else 0
            y_pos = int(pos[1]) if len(pos) > 1 else 0
            
            # Convert to data coordinates (adjusting for current slice position)
            # This is simplified but should work for most cases
            data_x = x_pos + current_step[-1] if len(current_step) > 0 else x_pos
            data_y = y_pos + current_step[-2] if len(current_step) > 1 else y_pos
            
            # Ensure within bounds
            data_x = max(0, min(data_x, shape[-1] - 1))
            data_y = max(0, min(data_y, shape[-2] - 1))
            
            self._drawing_start_pos = [data_x, data_y]
            self._current_crop_rect = None
            print(f"Starting crop box at: ({data_x}, {data_y})")
                
        except Exception as e:
            print(f"Error in mouse press handling: {e}")

    def _on_mouse_drag(self, event):
        """Handle mouse drag to update crop box."""
        if not self._drawing_crop_box or self._drawing_start_pos is None:
            return
            
        pos = event.position
        if pos is None:
            return
            
        try:
            # Get current displayed dimensions and slice position
            current_step = list(self.viewer.dims.current_step)
            shape = self._current_layer.data.shape
            
            # Simple coordinate extraction for 2D view
            x_pos = int(pos[0]) if len(pos) > 0 else 0
            y_pos = int(pos[1]) if len(pos) > 1 else 0
            
            # Convert to data coordinates
            data_x = x_pos + current_step[-1] if len(current_step) > 0 else x_pos
            data_y = y_pos + current_step[-2] if len(current_step) > 1 else y_pos
            
            # Ensure within bounds
            data_x = max(0, min(data_x, shape[-1] - 1))
            data_y = max(0, min(data_y, shape[-2] - 1))
            
            # Create rectangle from start to current position
            start_x, start_y = self._drawing_start_pos
            
            # Ensure minimum size
            if abs(data_x - start_x) >= 1 and abs(data_y - start_y) >= 1:
                rect = [
                    [start_x, start_y],
                    [data_x, start_y],
                    [data_x, data_y],
                    [start_x, data_y]
                ]
                
                # Update the crop box layer
                if self._crop_box_layer:
                    self._crop_box_layer.data = [np.array(rect)]
                    self._current_crop_rect = rect
                    print(f"Updating crop box: {start_x},{start_y} to {data_x},{data_y}")
                    
        except Exception as e:
            print(f"Error in mouse drag handling: {e}")

    def _on_mouse_release(self, event):
        """Handle mouse release to finish crop box."""
        if not self._drawing_crop_box:
            return
        # Mouse release doesn't need special handling here
        pass

    def _apply_crop_box_to_sliders(self, crop_rect):
        """Apply crop box coordinates to dimension sliders."""
        if not crop_rect or len(crop_rect) != 4:
            return
            
        try:
            # Extract coordinates from rectangle
            coords = np.array(crop_rect)
            min_x = int(np.min(coords[:, 0]))
            max_x = int(np.max(coords[:, 0]))
            min_y = int(np.min(coords[:, 1]))
            max_y = int(np.max(coords[:, 1]))
            
            # Find the spatial dimension controls (last 2 dimensions with size > 1)
            spatial_controls = []
            for i, control in enumerate(self._dim_controls):
                if control.dim_size > 1:
                    spatial_controls.append(control)
            
            # Apply to the last 2 spatial dimensions (usually X, Y)
            if len(spatial_controls) >= 2:
                # Apply to X dimension (second to last)
                x_control = spatial_controls[-2]
                x_control.range_slider.set_values((min_x, max_x))
                
                # Apply to Y dimension (last)
                y_control = spatial_controls[-1]
                y_control.range_slider.set_values((min_y, max_y))
                
                print(f"Crop box applied: X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]")
                print(f"Updated sliders: {x_control.label.text()} and {y_control.label.text()}")
            else:
                print("Could not find 2 spatial dimensions to apply crop box")
                
        except Exception as e:
            print(f"Error applying crop box to sliders: {e}")
        finally:
            # Clear the crop box after applying
            if self._crop_box_layer:
                self._crop_box_layer.data = []
