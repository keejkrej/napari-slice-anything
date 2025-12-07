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
    QFileDialog,
    QMessageBox,
)
from superqt import QLabeledDoubleRangeSlider

import napari
from napari.layers import Image
import os


class DimensionSliceControl(QWidget):
    """A widget with a range slider for controlling slice bounds on one dimension."""

    def __init__(self, dim_index: int, dim_size: int, dim_name: str = "", parent=None):
        super().__init__(parent)
        self.dim_index = dim_index
        self.dim_size = dim_size

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(dim_name or f"Dim {dim_index}")
        self.label.setMinimumWidth(60)
        layout.addWidget(self.label)

        self.range_slider = QLabeledDoubleRangeSlider(Qt.Orientation.Horizontal)
        self.range_slider.setRange(0, dim_size - 1)
        self.range_slider.setValue((0, dim_size - 1))
        self.range_slider.setDecimals(0)
        layout.addWidget(self.range_slider, stretch=1)

        self.size_label = QLabel(f"[{dim_size}]")
        self.size_label.setMinimumWidth(50)
        layout.addWidget(self.size_label)

    def get_slice(self) -> tuple[int, int]:
        """Return the current (min, max) slice values as integers."""
        val = self.range_slider.value()
        return (int(val[0]), int(val[1]) + 1)

    def set_dim_info(self, dim_size: int, dim_name: str = ""):
        """Update dimension size and name."""
        self.dim_size = dim_size
        self.range_slider.setRange(0, dim_size - 1)
        self.range_slider.setValue((0, dim_size - 1))
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
        
        self.save_btn = QPushButton("Save Sliced Layer")
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip("Save the currently sliced layer directly")
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        self._update_layer_combo()

    def _connect_signals(self):
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        self.apply_btn.clicked.connect(self._apply_slice)
        self.reset_btn.clicked.connect(self._reset_sliders)
        self.save_btn.clicked.connect(self._save_sliced_layer)

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
            self.save_btn.setEnabled(False)
            return

        self._current_layer = self.layer_combo.itemData(index)
        if self._current_layer is None:
            return

        shape = self._current_layer.data.shape
        self.shape_label.setText(str(shape))
        self._setup_dim_controls(shape)
        self.apply_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

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
                
                # Try to get the original layer's source info
                original_source = getattr(self._current_layer, '_source', None)
                if original_source is not None and hasattr(original_source, 'path') and original_source.path is not None:
                    # Create a derived filename for the sliced version
                    import os
                    original_path = original_source.path
                    base_name, ext = os.path.splitext(original_path)
                    sliced_path = f"{base_name}_sliced{ext}"
                    
                    new_layer._source = Source(
                        path=sliced_path,  # Derived path for sliced version
                        reader_plugin=getattr(original_source, 'reader_plugin', 'napari'),
                        plugin='napari-slice-anything'
                    )
                else:
                    # Create source with a generic sliced filename
                    new_layer._source = Source(
                        path=None,  # Let save system determine appropriate name
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

    def _save_sliced_layer(self):
        """Save the sliced data directly using numpy file I/O."""
        if self._current_layer is None:
            return
            
        # Get current slice configuration
        slices = []
        for control in self._dim_controls:
            start, stop = control.get_slice()
            slices.append(slice(start, stop))
        
        sliced_data = self._current_layer.data[tuple(slices)]
        
        if sliced_data.size == 0:
            QMessageBox.warning(self, "Warning", "No data to save - slice is empty")
            return
        
        # Create a smart default filename based on original layer name
        original_name = self._current_layer.name
        if original_name.endswith('_sliced'):
            base_name = original_name  # Don't double-add _sliced suffix
        else:
            base_name = f"{original_name}_sliced"
        
        # Ask user for save location
        file_path, file_ext = QFileDialog.getSaveFileName(
            self,
            "Save Sliced Data",
            base_name,
            "NumPy Array (*.npy);;TIFF Images (*.tiff *.tif);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            if file_path.endswith(('.npy', '.npz')):
                # Save as numpy array
                np.save(file_path, sliced_data)
                QMessageBox.information(self, "Success", f"Saved sliced data to {file_path}")
                
            elif file_path.endswith(('.tiff', '.tif')):
                # Save as TIFF using imageio
                import imageio.v3 as iio
                # For multi-dimensional data, save as individual slices or use compression
                if len(sliced_data.shape) > 2:
                    # Handle multi-dimensional data
                    if len(sliced_data.shape) == 3:
                        # 3D data - save as multi-page TIFF
                        iio.imwrite(file_path, sliced_data)
                    else:
                        # Higher dimensions - flatten and save
                        # Take first 2D slice for demonstration
                        if sliced_data.dtype == np.complex64 or sliced_data.dtype == np.complex128:
                            # Handle complex data by taking magnitude
                            data_to_save = np.abs(sliced_data)
                        else:
                            data_to_save = sliced_data
                        iio.imwrite(file_path, data_to_save.astype(np.float32))
                else:
                    # 2D data
                    if sliced_data.dtype == np.complex64 or sliced_data.dtype == np.complex128:
                        data_to_save = np.abs(sliced_data)
                    else:
                        data_to_save = sliced_data
                    iio.imwrite(file_path, data_to_save)
                    
                QMessageBox.information(self, "Success", f"Saved sliced data to {file_path}")
                
            else:
                # Default to numpy format
                if not file_path.endswith('.npy'):
                    file_path += '.npy'
                np.save(file_path, sliced_data)
                QMessageBox.information(self, "Success", f"Saved sliced data to {file_path}")
                
        except Exception as e:
            error_msg = f"Failed to save data: {str(e)}"
            QMessageBox.critical(self, "Error", error_msg)
            print(error_msg)
            
    def _reset_sliders(self):
        """Reset all sliders to full range."""
        if self._current_layer is None:
            return

        shape = self._current_layer.data.shape
        for control, size in zip(self._dim_controls, shape):
            control.range_slider.setValue((0, size - 1))
