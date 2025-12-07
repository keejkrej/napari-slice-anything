# napari-slice-anything

[![License BSD-3](https://img.shields.io/pypi/l/napari-slice-anything.svg?color=green)](https://github.com/jack/napari-slice-anything/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-slice-anything.svg?color=green)](https://pypi.org/project/napari-slice-anything)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-slice-anything.svg?color=green)](https://python.org)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-slice-anything)](https://napari-hub.org/plugins/napari-slice-anything)

A napari plugin for slicing multidimensional image stacks with intuitive range sliders.

## Features

- **Range sliders for each dimension**: Easily select the range of data to extract for any dimension
- **Live preview**: See the shape of your data as you adjust sliders
- **Non-destructive**: Creates new layers with sliced data, preserving originals
- **Works with any dimensionality**: Handles 2D, 3D, 4D, and higher-dimensional data

## Installation

You can install `napari-slice-anything` via [pip]:

    pip install napari-slice-anything

## Usage

1. Open napari and load an image
2. Open the plugin from `Plugins > Slice Anything`
3. Select the image layer you want to slice
4. Adjust the range sliders for each dimension
5. Click "Apply Slice" to create a new layer with the sliced data

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-slice-anything" is free and open source software.
