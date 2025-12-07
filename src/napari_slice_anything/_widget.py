"""Main widget for slicing multidimensional image stacks."""

from typing import Optional

import numpy as np
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QVBoxLayout, QWidget

import napari
from napari.layers import Image

from .widgets import (
    LayerSelector,
    DimensionControls,
    ButtonControls,
    CropFromShapeHandler,
)


class SliceAnythingWidget(QWidget):
    """A napari widget for slicing multidimensional image stacks using range sliders."""

    def __init__(self, napari_viewer: napari.Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self._current_layer: Optional[Image] = None

        # Initialize atomic components
        self.layer_selector = LayerSelector(napari_viewer)
        self.dimension_controls = DimensionControls()
        self.button_controls = ButtonControls()
        self.crop_handler = CropFromShapeHandler(napari_viewer, self.dimension_controls)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(self.layer_selector)
        layout.addWidget(self.dimension_controls)
        layout.addWidget(self.button_controls)
        layout.addStretch()

    def _connect_signals(self):
        """Connect signals between components."""
        # Layer selector signals
        self.layer_selector.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        
        # Button signals
        self.button_controls.apply_btn.clicked.connect(self._apply_slice)
        self.button_controls.reset_btn.clicked.connect(self._reset_sliders)
        self.button_controls.draw_box_btn.clicked.connect(self._apply_crop_from_shape)
        
        # Crop handler signals
        self.crop_handler.crop_applied.connect(self._on_crop_applied)
        self.crop_handler.crop_failed.connect(self._on_crop_failed)

    def _on_layer_changed(self, index: int):
        """Handle layer selection change."""
        self._current_layer = self.layer_selector.get_current_layer()
        
        if self._current_layer is None:
            self._clear_dim_controls()
            self._update_button_states(False)
            return

        # Setup dimension controls for the selected layer
        self.dimension_controls.setup_controls(self._current_layer)
        self._update_button_states(True)

    def _clear_dim_controls(self):
        """Remove all dimension controls."""
        self.dimension_controls.clear_controls()

    def _update_button_states(self, layer_selected: bool):
        """Update button enable states based on layer selection."""
        self.button_controls.set_apply_enabled(layer_selected)
        self.button_controls.set_reset_enabled(layer_selected)
        self.button_controls.set_crop_enabled(layer_selected)

    def _apply_slice(self):
        """Apply the current slice configuration to create a new layer."""
        if self._current_layer is None:
            return

        slices = self.dimension_controls.get_all_slices()
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
                    'slice_bounds': [c.get_slice() for c in self.dimension_controls._dim_controls]
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
        self.crop_handler.apply_crop_from_shape()

    def _on_crop_applied(self):
        """Handle successful crop application."""
        pass  # Could add user feedback here

    def _on_crop_failed(self, error_message: str):
        """Handle crop application failure."""
        pass  # Could add user feedback here

    def _reset_sliders(self):
        """Reset all dimension controls to full range."""
        if self._current_layer is None:
            return

        self.dimension_controls.reset_all()
