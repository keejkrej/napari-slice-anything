"""Crop from shape handler component."""

import numpy as np
from qtpy.QtCore import QObject, Signal

import napari
from napari.layers import Shapes


class CropFromShapeHandler(QObject):
    """Handler for applying crop areas from selected shapes."""

    # Signals
    crop_applied = Signal()
    crop_failed = Signal(str)

    def __init__(self, viewer: napari.Viewer, dimension_controls=None, parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.dimension_controls = dimension_controls

    def apply_crop_from_shape(self):
        """Apply crop area from selected shape in a shapes layer."""
        # Find the currently selected shapes layer
        shapes_layer = self._find_selected_shapes_layer()
        if shapes_layer is None:
            self.crop_failed.emit("No selected shapes found")
            return False
            
        try:
            # Get the first selected shape's data
            selected_indices = list(shapes_layer.selected_data)
            if not selected_indices:
                self.crop_failed.emit("No shape selected")
                return False
                
            shape_index = selected_indices[0]
            shape_data = shapes_layer.data[shape_index]
            
            # Extract bounding box coordinates
            if len(shape_data) >= 4:  # Rectangle or polygon
                coords = np.array(shape_data)
                
                # Handle any dimensional coordinate format by extracting last 2 dimensions (Y, X)
                # This works for 2D, 3D, 4D, 5D, etc. - always take the spatial dimensions
                ndim = coords.shape[1]
                
                # Extract spatial coordinates (last 2 dimensions: Y, X)
                min_y = int(np.min(coords[:, ndim-2]))  # second to last dimension (Y)
                max_y = int(np.max(coords[:, ndim-2]))  # second to last dimension (Y)
                min_x = int(np.min(coords[:, ndim-1]))  # last dimension (X)
                max_x = int(np.max(coords[:, ndim-1]))  # last dimension (X)
                
                # Try to convert to data coordinates if the shapes layer has transformation
                try:
                    if hasattr(shapes_layer, 'data_to_world'):
                        # Extract spatial coordinates (last 2 dimensions regardless of total dimensions)
                        spatial_coords = coords[:, [ndim-2, ndim-1]]  # Y, X coordinates
                            
                        world_coords = np.column_stack([spatial_coords[:, 0], spatial_coords[:, 1]])
                        data_coords = shapes_layer.data_to_world(world_coords)
                        min_x_data = int(np.min(data_coords[:, 0]))
                        max_x_data = int(np.max(data_coords[:, 0]))
                        min_y_data = int(np.min(data_coords[:, 1]))
                        max_y_data = int(np.max(data_coords[:, 1]))
                        
                        # Use data coordinates if they seem reasonable
                        if abs(max_x_data - min_x_data) > 1 and abs(max_y_data - min_y_data) > 1:
                            min_x, max_x = min_x_data, max_x_data
                            min_y, max_y = min_y_data, max_y_data
                        
                except Exception:
                    pass  # Use processed coordinates if conversion fails
                
                # Apply crop to dimension controls
                return self._apply_crop_to_dimensions(min_x, max_x, min_y, max_y)
            else:
                self.crop_failed.emit("Selected shape doesn't have enough vertices for a bounding box")
                return False
                
        except Exception:
            self.crop_failed.emit("Error applying crop from shape")
            return False

    def _find_selected_shapes_layer(self) -> Shapes:
        """Find the currently selected shapes layer."""
        for layer in self.viewer.layers:
            if isinstance(layer, Shapes) and len(layer.data) > 0:
                # Check if any shapes are selected
                if hasattr(layer, 'selected_data') and layer.selected_data:
                    return layer
        return None

    def _apply_crop_to_dimensions(self, min_x: int, max_x: int, min_y: int, max_y: int) -> bool:
        """Apply crop coordinates to the dimension controls."""
        if self.dimension_controls is None:
            self.crop_failed.emit("Dimension controls not available")
            return False

        # Find the current layer to get bounds
        current_layer = None
        for layer in self.viewer.layers:
            if isinstance(layer, napari.layers.Image):
                current_layer = layer
                break

        if current_layer is None:
            self.crop_failed.emit("No image layer found")
            return False

        # Ensure coordinates are within bounds of the current layer
        shape = current_layer.data.shape
        # Clamp to valid range
        min_x = max(0, min(min_x, shape[-1] - 1))
        max_x = max(0, min(max_x, shape[-1] - 1))
        min_y = max(0, min(min_y, shape[-2] - 1))
        max_y = max(0, min(max_y, shape[-2] - 1))
        
        # Find spatial dimension controls (last 2 dimensions with size > 1)
        spatial_controls = self.dimension_controls.get_spatial_dimensions()
        
        if len(spatial_controls) >= 2:
            # Apply to Y dimension (second to last spatial control)
            y_control = spatial_controls[-2]
            y_control.min_edit.setText(str(min_y))
            y_control.max_edit.setText(str(max_y))
            
            # Apply to X dimension (last spatial control)
            x_control = spatial_controls[-1]
            x_control.min_edit.setText(str(min_x))
            x_control.max_edit.setText(str(max_x))
            
            self.crop_applied.emit()
            return True
        else:
            self.crop_failed.emit("Could not find 2 spatial dimensions to apply crop")
            return False
