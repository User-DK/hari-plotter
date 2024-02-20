from __future__ import annotations

import math
import warnings
from abc import ABC
from typing import (Any, Dict, Iterator, List, Optional, Sequence, Tuple, Type,
                    Union)

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import seaborn as sns

from .color_scheme import ColorScheme
from .interface import Interface
from .parameters import (BoolParameter, FloatParameter, ListParameter,
                         NoneOrFloatParameter, NoneRangeParameter, Parameter)
from .plotter import Plotter


class Plot(ABC):
    def __init__(self):
        self.color_scheme: ColorScheme = None
        self.parameters: Tuple[str] = None
        self.scale: Tuple[str] = None
        self.show_x_label: bool = None
        self.show_y_label: bool = None
        self._x_lim: Sequence[float] | None = None
        self._y_lim: Sequence[float] | None = None

    @staticmethod
    def settings(interface: Interface):
        return []

    @classmethod
    def from_qt(cls, qt_settings: dict):
        return cls(**qt_settings)

    def _parse_axis_limit_reference(self, reference_str):
        """
        Parse the axis limit reference string.

        Args:
            reference_str (str): The reference string (e.g., 'x@1,0').

        Returns:
            tuple: A tuple containing the axis ('x' or 'y'), row index, and column index.
        """
        ref_axis, ref_indices = reference_str.split('@')
        ref_row, ref_col = map(int, ref_indices.split(','))
        return ref_axis, ref_row, ref_col

    def plot_dependencies(self):
        dependencies = {'before': [], 'after': []}

        for value in [self._x_lim, self._y_lim]:
            if isinstance(value, str):
                # Assuming format is 'x(y)@row,col'
                ref_plot = tuple(map(int, value[2:].split(',')))
                # Add edge with (row, col) only
                dependencies['after'].append(ref_plot)
        return dependencies

    def get_limits(self, axis_limits: dict) -> List[Tuple[float | None]]:
        final_limits = []
        parameters = list(self.parameters) + [None] * \
            max(2 - len(self.parameters), 0)
        for i_lim, scale, parameter in zip((self._x_lim, self._y_lim), self.scale, parameters):
            if parameter == 'Time':
                final_limits.append((None, None))
            elif scale == 'Tanh':
                final_limits.append((-1., 1.))
            elif i_lim is None:
                final_limits.append((None, None))
            elif isinstance(i_lim, str):
                ref_axis, ref_row, ref_col = self._parse_axis_limit_reference(
                    i_lim)
                if (ref_row, ref_col) in axis_limits:
                    final_limits.append(
                        axis_limits[(ref_row, ref_col)][0 if ref_axis == 'x' else 1])
                else:
                    raise ValueError('Render order failure')
            else:
                final_limits.append(i_lim)

        return final_limits

    @staticmethod
    def transform_data(data_list, transform_parameter: str = 'Nodes'):
        # Extract unique transform_parameter's and sort them
        # print(f'{list(data_list[0].keys()) = }')
        # print(f'{transform_parameter = }')
        # print(f'{data_list[0][transform_parameter] = }')
        transform_parameter_values = {
            transform_parameter_value for data in data_list for transform_parameter_value in data[transform_parameter]}
        transform_parameter_values = {
            elem for elem in transform_parameter_values if elem is not None}
        # print(f'{transform_parameter_values = }')
        transform_parameter_values = sorted(transform_parameter_values)
        # print(f'{transform_parameter_values = }')
        transform_parameter_value_index = {transform_parameter_value: i for i,
                                           transform_parameter_value in enumerate(transform_parameter_values)}
        # print(f'{transform_parameter_value_index = }')

        # Extract time steps
        time_steps = [data['Time'] for data in data_list]

        # Initialize parameters dictionary
        # print(f'{list(data_list[0].keys()) = }')
        params = {key: np.full((len(transform_parameter_values), len(time_steps)), np.nan)
                  for key in data_list[0] if key not in [transform_parameter, 'Time', 'Nodes']}

        # Fill in the parameter values
        for t, data in enumerate(data_list):
            for param in params:
                if param in data and param != 'Nodes':
                    # Map each transform_parameter_value's value to the corresponding row in the parameter's array
                    for transform_parameter_value, value in zip(data[transform_parameter], data[param]):
                        if transform_parameter_value is not None:
                            # print(f'{transform_parameter_value = }')
                            idx = transform_parameter_value_index[transform_parameter_value]
                            # print(f'{param = } {idx = } { t = } {value = }')
                            params[param][idx, t] = value
                        else:
                            pass
                            # print(f'{param = } {value = } ')

        return {
            'Time': np.array(time_steps),
            transform_parameter: transform_parameter_values,
            **params
        }

    def get_static_plot_requests(self):
        return []

    def get_dynamic_plot_requests(self):
        return []

    def get_track_clusterings_requests(self):
        return []

    @staticmethod
    def is_available(interface: Interface):
        ''' Returns True if available for this interface and comment why'''
        return True, ''

    def settings_to_code(self) -> str:
        return ''


@Plotter.plot_type("Histogram")
class plot_histogram(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str],
                 scale: Optional[Tuple[str] | None] = None,
                 rotated: Optional[bool] = False,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, histogram_color: str | dict | float | None = None):
        self.color_scheme: ColorScheme = color_scheme
        self.parameters: Tuple[str] = tuple(parameters)
        self.scale: Tuple[str] = tuple(scale or ('Linear', 'Linear'))
        self.rotated: bool = rotated
        self.show_x_label: bool = show_x_label
        self.show_y_label: bool = show_y_label
        self._x_lim: Sequence[float] | None = x_lim
        self._y_lim: Sequence[float] | None = y_lim

        def histogram_color_to_histogram_color_settings(histogram_color) -> dict:
            if isinstance(histogram_color, dict):
                # check if only 'mode' and 'settings' in dict
                if all(key in {'mode', 'settings'} for key in histogram_color.keys()):
                    raise ValueError(
                        'Histogram color is incorrectly formatted')
                return histogram_color
            if isinstance(histogram_color, (str, float)):
                return {'mode': 'Constant Color', 'settings': {'color': histogram_color}}
            else:
                return {'mode': 'Constant Color'}

        self.histogram_color_settings: dict = histogram_color_to_histogram_color_settings(
            histogram_color)

        if self.histogram_color_settings['mode'] not in self.color_scheme.method_logger['Distribution Color']['modes']:
            raise ValueError('Histogram color is incorrectly formatted')

    def settings_to_code(self) -> str:
        return ('\'parameters\':'+str(self.parameters) +
                ',\'scale\':'+str(self.scale) +
                ',\'rotated\':'+str(self.rotated) +
                ',\'show_x_label\':'+str(self.show_x_label) +
                ',\'show_y_label\':'+str(self.show_y_label) +
                ',\'x_lim\':'+str(self._x_lim) +
                ',\'y_lim\':'+str(self._y_lim) +
                ',\'histogram_color\':'+str(self.histogram_color_settings))

    @staticmethod
    def settings(interface: Interface) -> List[Parameter]:
        return [ListParameter(name='Parameter', parameter_name='parameter', arguments=interface.node_parameters, comment='Parameter of the histogram'),
                ListParameter(name='Scale', parameter_name='scale', arguments=[
                              'Linear', 'Tanh'], comment='Scale of the parameter'),
                BoolParameter(name='Rotate', parameter_name='rotated', default_value=False,
                              comment='Should the histogram be rotated?'),
                BoolParameter(
                    name='Show X Label', parameter_name='show_x_label', default_value=True, comment=''),
                BoolParameter(
                    name='Show Y Label', parameter_name='show_y_label', default_value=True, comment=''),
                NoneRangeParameter(name='X Limit', parameter_name='x_lim',
                                   default_min_value=None, default_max_value=None, limits=(None, None), comment=''),
                NoneRangeParameter(name='Y Limit', parameter_name='y_lim',
                                   default_min_value=None, default_max_value=None, limits=(None, None), comment=''),
                ]

    @staticmethod
    def qt_to_settings(qt_settings: dict) -> dict:
        '''
        Transforms dict of settings from PyQT GUI to the dict that will be used for class init.
        '''
        settings = qt_settings.copy()

        # Extract the value of 'parameter' and remove it from settings
        parameter_value = settings.pop('parameter', None)

        settings['parameters'] = (parameter_value,)

        settings['scale'] = (settings['scale'], 'Linear')

        return settings

    def get_dynamic_plot_requests(self) -> List[dict]:
        return [{'method': 'calculate_node_values', 'settings': {'parameters': self.parameters, 'scale': self.scale}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        """
        Plot a histogram on the given ax with the provided data data.

        Parameters:
        -----------
        ax : plt.Axes
            Axes object where the histogram will be plotted.
        data : list[float]
            List containing parameter values.
        scale : str, optional
            The scale for the x-axis. Options: 'Linear' or 'Tanh'.
        rotated : bool, optional
            If True, the histogram is rotated to be horizontal.
        x_lim : Optional[Sequence[float] | None]
            Limits of the x-axis.
        y_lim : Optional[Sequence[float] | None]
            Limits of the y-axis.
        """

        if len(self.parameters) != 1:
            raise ValueError('Histogram expects only one parameter')

        x_lim, y_lim = self.get_limits(axis_limits)
        data = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]

        nodes = data['Nodes']

        parameter = self.parameters[0]
        values = np.array(data[parameter])
        valid_indices = ~np.isnan(values)
        values = values[valid_indices]

        histogram_color = self.color_scheme.distribution_color(
            nodes, **self.histogram_color_settings)

        if self.rotated:
            if self.scale[1] == 'Tanh':
                values = np.tanh(values)

            y_lim = [np.nanmin(values) if y_lim[0] is None else y_lim[0], np.nanmax(
                values) if y_lim[1] is None else y_lim[1]]

            values = values[(values >= y_lim[0]) & (values <= y_lim[1])]

            sns.kdeplot(y=values, ax=ax, fill=True, color=histogram_color)
            sns.histplot(y=values, kde=False, ax=ax,
                         binrange=y_lim, element="step", fill=False, stat="density")

            if self.show_y_label:
                ax.set_ylabel(Plotter._parameter_dict.get(
                    parameter, parameter))
            if self.show_x_label:
                ax.set_xlabel('Density')

        else:

            if self.scale[0] == 'Tanh':
                values = np.tanh(values)

            x_lim = [np.nanmin(values) if x_lim[0] is None else x_lim[0], np.nanmax(
                values) if x_lim[1] is None else x_lim[1]]

            values = values[(values >= x_lim[0]) & (values <= x_lim[1])]

            sns.kdeplot(data=values, ax=ax, fill=True, color=histogram_color)
            sns.histplot(data=values, kde=False, ax=ax,
                         binrange=x_lim, element="step", fill=False, stat="density")

            if self.show_x_label:
                ax.set_xlabel(Plotter._parameter_dict.get(
                    parameter, parameter))
            if self.show_y_label:
                ax.set_ylabel('Density')

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)
        if x_lim is not None:
            ax.set_xlim(*x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)


@Plotter.plot_type("Hexbin")
class plot_hexbin(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str],
                 scale: Optional[Tuple[str] | None] = None,
                 rotated: Optional[bool] = False,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, colormap: str | None = None, show_colorbar: bool = False):
        self.color_scheme = color_scheme
        self.parameters = tuple(parameters)
        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.rotated = rotated
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.show_colorbar = show_colorbar

        def colormap_to_colormap_settings(colormap) -> dict:
            if isinstance(colormap, dict):
                # check if only 'mode' and 'settings' in dict
                if all(key in {'mode', 'settings'} for key in colormap.keys()):
                    raise ValueError(
                        'Colormap is incorrectly formatted')
                return colormap
            if isinstance(colormap, (str, float)):
                return {'mode': 'Independent Colormap', 'settings': {'colormap': colormap}}
            else:
                return {'mode': 'Independent Colormap'}

        self.colormap_settings = colormap_to_colormap_settings(colormap)

        if self.colormap_settings['mode'] not in self.color_scheme.method_logger['Color Map']['modes']:
            raise ValueError('Colormap is incorrectly formatted')

    def settings_to_code(self) -> str:
        return ('\'parameters\':'+str(self.parameters) +
                ',\'scale\':'+str(self.scale) +
                ',\'rotated\':'+str(self.rotated) +
                ',\'show_x_label\':'+str(self.show_x_label) +
                ',\'show_y_label\':'+str(self.show_y_label) +
                ',\'x_lim\':'+str(self._x_lim) +
                ',\'y_lim\':'+str(self._y_lim) +
                ',\'show_colorbar\':'+str(self.show_colorbar))

    @staticmethod
    def settings(interface: Interface) -> List[Parameter]:
        return [ListParameter(name='X parameter', parameter_name='x_parameter', arguments=interface.node_parameters, comment=''),
                ListParameter(name='X scale', parameter_name='x_scale', arguments=[
                              'Linear', 'Tanh'], comment=''),
                ListParameter(name='Y parameter', parameter_name='y_parameter',
                              arguments=interface.node_parameters, comment=''),
                ListParameter(name='Y scale', parameter_name='y_scale', arguments=[
                              'Linear', 'Tanh'], comment=''),
                BoolParameter(name='Rotate', parameter_name='rotated', default_value=False,
                              comment='Should the plot be rotated?'),
                BoolParameter(
                    name='Show X Label', parameter_name='show_x_label', default_value=True, comment=''),
                BoolParameter(
                    name='Show Y Label', parameter_name='show_y_label', default_value=True, comment=''),
                NoneRangeParameter(name='X Limit', parameter_name='x_lim',
                                   default_min_value=None, default_max_value=None, limits=(None, None), comment=''),
                NoneRangeParameter(name='Y Limit', parameter_name='y_lim',
                                   default_min_value=None, default_max_value=None, limits=(None, None), comment=''),
                BoolParameter(
                    name='Show Colorbar', parameter_name='show_colorbar', default_value=False, comment=''),
                ]

    @staticmethod
    def qt_to_settings(qt_settings: dict) -> dict:
        # Copy qt_settings to avoid modifying the original dictionary
        settings = qt_settings.copy()

        # Extract the value of 'parameter' and remove it from settings
        x_parameter_value = settings.pop('x_parameter', None)
        y_parameter_value = settings.pop('y_parameter', None)

        x_scale = settings.pop('x_scale', None)
        y_scale = settings.pop('y_scale', None)

        settings['parameters'] = (x_parameter_value, y_parameter_value)

        settings['scale'] = (x_scale, y_scale)

        return settings

    def get_dynamic_plot_requests(self):
        return [{'method': 'calculate_node_values', 'settings': {'parameters': self.parameters, 'scale': self.scale}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        """
        Plot a hexbin on the given ax with the provided x and y values.

        Parameters:
        -----------
        ax : plt.Axes
            Axes object where the hexbin will be plotted.
        x_values, y_values : list[float]
            Lists containing x-values and y-values
        extent : list[float], optional
            The bounding box in data coordinates that the hexbin should fill.
        colormap : str, optional
            The colormap to be used for hexbin coloring.
        cmax : float, optional
            The maximum number of counts in a hexbin for colormap scaling.
        scale : list, optional
            Scale for the plot values (x and y). Options: 'Linear' or 'Tanh'. Default is 'Linear' for both.
        show_colorbar : bool, optional
        """

        x_lim, y_lim = self.get_limits(axis_limits)

        data = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]

        x_parameter = self.parameters[0]
        y_parameter = self.parameters[1]
        x_values = np.array(data[x_parameter])
        y_values = np.array(data[y_parameter])
        nodes = data['Nodes']
        colormap = self.color_scheme.colorbar(nodes, **self.colormap_settings)

        # Find indices where neither x_values nor y_values are NaN
        valid_indices = ~np.isnan(x_values) & ~np.isnan(y_values)

        # Filter the values using these indices
        x_values = x_values[valid_indices]
        y_values = y_values[valid_indices]

        if self.scale[0] == 'Tanh':
            x_values = np.tanh(x_values)

        if self.scale[1] == 'Tanh':
            y_values = np.tanh(y_values)

        if x_lim == (None, None):
            x_lim = [-1, 1] if self.scale[0] == 'Tanh' else [
                np.nanmin(x_values), np.nanmax(x_values)]
        if y_lim == (None, None):
            y_lim = [-1, 1] if self.scale[1] == 'Tanh' else [
                np.nanmin(y_values), np.nanmax(y_values)]

        extent = x_lim+y_lim

        delta_x = 0.1*(extent[1]-extent[0])
        x_field_extent = [extent[0]-delta_x, extent[1]+delta_x]

        delta_y = 0.1*(extent[3]-extent[2])
        y_field_extent = [extent[2]-delta_y, extent[3]+delta_y]

        field_extent = x_field_extent + y_field_extent

        ax.imshow([[0, 0], [0, 0]], cmap=colormap,
                  interpolation='nearest', aspect='auto', extent=field_extent)

        hb = ax.hexbin(x_values, y_values, gridsize=50,
                       bins='log', extent=extent, cmap=colormap)

        # Create a background filled with the `0` value of the colormap
        ax.imshow([[0, 0], [0, 0]], cmap=colormap,
                  interpolation='nearest', aspect='auto', extent=extent)
        # Create the hexbin plot

        hb = ax.hexbin(x_values, y_values, gridsize=50, cmap=colormap,
                       bins='log', extent=extent)

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if x_lim is not None:
            ax.set_xlim(*x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)

        if self.show_colorbar:
            plt.colorbar(hb, ax=ax)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                self.parameters[0], self.parameters[0]))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                self.parameters[1], self.parameters[1]))


@Plotter.plot_type("Scatter")
class plot_scatter(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str],
                 scale: Optional[Tuple[str] | None] = None,
                 rotated: Optional[bool] = False,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, color: Optional[str | None] = None, marker: Optional[str | None] = None):
        self.parameters = tuple(parameters)
        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.rotated = rotated
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.color_scheme = color_scheme

        def scatter_color_to_scatter_color_settings(scatter_color) -> dict:
            if isinstance(scatter_color, dict):
                # check if only 'mode' and 'settings' in dict
                if all(key in {'mode', 'settings'} for key in scatter_color.keys()):
                    raise ValueError(
                        'Histogram color is incorrectly formatted')
                return scatter_color
            if isinstance(scatter_color, (str, float)):
                return {'mode': 'Constant Color', 'settings': {'color': scatter_color}}
            else:
                return {'mode': 'Constant Color'}

        self.scatter_color_settings: dict = scatter_color_to_scatter_color_settings(
            color)

        if self.scatter_color_settings['mode'] not in self.color_scheme.method_logger['Scatter Color']['modes']:
            raise ValueError('Histogram color is incorrectly formatted')

        def scatter_marker_to_scatter_marker_settings(scatter_marker) -> dict:
            if isinstance(scatter_marker, dict):
                # check if only 'mode' and 'settings' in dict
                if all(key in {'mode', 'settings'} for key in scatter_marker.keys()):
                    raise ValueError(
                        'Histogram marker is incorrectly formatted')
                return scatter_marker
            if isinstance(scatter_marker, (str, float)):
                return {'mode': 'Constant Marker', 'settings': {'marker': scatter_marker}}
            else:
                return {'mode': 'Constant Marker'}

        self.scatter_marker_settings: dict = scatter_marker_to_scatter_marker_settings(
            marker)

    def get_dynamic_plot_requests(self):
        return [{'method': 'calculate_node_values', 'settings': {'parameters': self.parameters, 'scale': self.scale}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        """
        Plot a scatter plot on the given ax with the provided x and y values.

        Parameters:
        -----------
        ax : plt.Axes
            Axes object where the scatter plot will be plotted.
        data : defaultdict[List[float]]
            A dictionary containing lists of x and y values.
        parameters : tuple[str]
            A tuple containing the names of the parameters to be plotted.
        x_lim, y_lim : Optional[Sequence[float]]
            The limits for the x and y axes.
        color : Optional[str]
            The color of the markers.
        marker : str
            The shape of the marker.
        show_x_label, show_y_label : bool
            Flags to show or hide the x and y labels.
        """

        x_lim, y_lim = self.get_limits(axis_limits)

        data = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]

        x_parameter, y_parameter = self.parameters
        x_values = np.array(data[x_parameter])
        y_values = np.array(data[y_parameter])
        nodes = data['Nodes']
        # print(f'{nodes = }')

        # Remove NaN values
        valid_indices = ~np.isnan(x_values) & ~np.isnan(y_values)
        x_values = x_values[valid_indices]
        y_values = y_values[valid_indices]
        valid_nodes = [nodes[i] for i in np.where(valid_indices)[0]]

        if self.scale[0] == 'Tanh':
            x_values = np.tanh(x_values)

        if self.scale[1] == 'Tanh':
            y_values = np.tanh(y_values)

        colors = self.color_scheme.scatter_colors_nodes(
            valid_nodes, **self.scatter_color_settings)
        markers = self.color_scheme.scatter_markers_nodes(
            valid_nodes, **self.scatter_marker_settings)
        ax.scatter(x_values, y_values,
                   color=colors, marker=markers)

        # Setting the plot limits
        if x_lim is not None:
            ax.set_xlim(*x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                x_parameter, x_parameter))

        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                y_parameter, y_parameter))


@Plotter.plot_type("Clustering: Centroids")
class plot_clustering_centroids(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str], clustering_settings: dict = {},
                 scale: Optional[Tuple[str] | None] = None,
                 rotated: Optional[bool] = False,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, resolution: int = 100):
        self.parameters = tuple(parameters)
        self.clustering_settings = clustering_settings
        if 'clustering_parameters' not in self.clustering_settings:
            self.clustering_settings['clustering_parameters'] = self.parameters

        # print(f'{self.clustering_settings = }')
        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.rotated = rotated
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.resolution = resolution

        # self.data_key = Interface.request_to_tuple(
        #     self.get_dynamic_plot_requests()[0])

    def get_dynamic_plot_requests(self):
        return [{'method': 'get_clustering', 'settings': {'parameters': self.parameters, 'scale': self.scale, 'clustering_settings': self.clustering_settings}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        """
        Plots the decision boundaries for a 2D slice of the clustering object's data.

        Args:
        - x_feature_index (int): The index of the feature to be plotted on the x-axis.
        - y_feature_index (int): The index of the feature to be plotted on the y-axis.
        - plot_limits (tuple): A tuple containing the limits of the plot: (x_min, x_max, y_min, y_max).
        - resolution (int): The number of points to generate in the mesh for the plot.

        Returns:
        None
        """

        x_lim, y_lim = self.get_limits(axis_limits)
        clustering = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]

        x_feature_name, y_feature_name = self.parameters

        x_feature_index, y_feature_index = clustering.get_indices_from_parameters(
            [x_feature_name, y_feature_name])

        # Plot centroids if they are 2D
        centroids = clustering.centroids()
        if centroids.shape[1] == 2:
            centroids_x = centroids[:, x_feature_index]
            centroids_y = centroids[:, y_feature_index]
            if self.scale[0] == 'Tanh':
                centroids_x = np.tanh(centroids_x)
            if self.scale[1] == 'Tanh':
                centroids_y = np.tanh(centroids_y)

            ax.scatter(centroids_x, centroids_y,
                       color="red",
                       label="Centroids",
                       marker="X",
                       )
        else:
            warnings.warn(
                f'centroids.shape[1] != 2, it is {centroids.shape[1]}. Clusters centroids are not shown on a plot')

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                self.parameters[0], self.parameters[0]))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                self.parameters[1], self.parameters[1]))


@Plotter.plot_type("Clustering: Scatter")
class plot_clustering_scatter(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str], clustering_settings: dict = {},
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, resolution: int = 100, show_clustering_labels: bool = False):
        self.parameters = tuple(parameters)
        self.clustering_settings = clustering_settings
        if 'clustering_parameters' not in self.clustering_settings:
            self.clustering_settings['clustering_parameters'] = self.parameters

        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.resolution = resolution
        self.show_clustering_labels = show_clustering_labels

        self.cluster_colors = {}  # Initialize the cluster colors dictionary

        # self.data_key = Interface.request_to_tuple(
        #     self.get_dynamic_plot_requests()[0])

    def get_dynamic_plot_requests(self):
        return [{'method': 'get_clustering', 'settings': {'parameters': self.parameters, 'scale': self.scale, 'clustering_settings': self.clustering_settings}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        """
        Plots the decision scatter for a 2D slice of the clustering object's data.
        """

        x_lim, y_lim = self.get_limits(axis_limits)
        clustering = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]
        cluster_labels = clustering.cluster_labels

        x_feature_name, y_feature_name = self.parameters

        x_feature_index, y_feature_index = clustering.get_indices_from_parameters(
            [x_feature_name, y_feature_name])

        data = clustering.get_values([x_feature_name, y_feature_name])

        for label, points in zip(cluster_labels, data):
            x_points = points[:, 0]
            y_points = points[:, 1]

            if self.scale[0] == 'Tanh':
                x_points = np.tanh(x_points)
            if self.scale[1] == 'Tanh':
                y_points = np.tanh(y_points)

            # Assign a new color if the label is not in cluster_colors, else use the existing color
            if label not in self.cluster_colors:
                self.cluster_colors[label] = plt.cm.coolwarm(np.random.rand())
            color = self.cluster_colors[label]

            ax.scatter(x_points, y_points, color=color,
                       label=label if self.show_clustering_labels else "")

        if self.show_clustering_labels:
            ax.legend()

        # Setting the plot limits
        if x_lim is not None:
            ax.set_xlim(x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                self.parameters[0], self.parameters[0]))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                self.parameters[1], self.parameters[1]))


@Plotter.plot_type("Clustering: Fill")
class plot_clustering_fill(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str], clustering_settings: dict = {},
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, resolution: int = 100):
        self.parameters = tuple(parameters)
        self.clustering_settings = clustering_settings
        if 'clustering_parameters' not in self.clustering_settings:
            self.clustering_settings['clustering_parameters'] = self.parameters

        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.resolution = resolution

        # self.data_key = Interface.request_to_tuple(
        #     self.get_dynamic_plot_requests()[0])

    def get_dynamic_plot_requests(self):
        return [{'method': 'get_clustering', 'settings': {'parameters': self.parameters, 'scale': self.scale, 'clustering_settings': self.clustering_settings}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        x_lim, y_lim = self.get_limits(axis_limits)
        clustering = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]

        x_feature_name, y_feature_name = self.parameters
        x_feature_index, y_feature_index = clustering.get_indices_from_parameters(
            [x_feature_name, y_feature_name])

        xx, yy = np.meshgrid(
            np.linspace(x_lim[0], x_lim[1], self.resolution), np.linspace(
                y_lim[0], y_lim[1], self.resolution)
        )

        mesh_points = np.c_[xx.ravel(), yy.ravel()]
        mesh_points_scaled = np.array(mesh_points)
        if self.scale[0] == 'Tanh':
            mesh_points_scaled[:, 0] = np.arctanh(mesh_points_scaled[:, 0])
        if self.scale[1] == 'Tanh':
            mesh_points_scaled[:, 1] = np.arctanh(mesh_points_scaled[:, 1])

        Z = clustering.predict_clustering(mesh_points_scaled)
        Z = Z.reshape(xx.shape)

        im = ax.imshow(Z, extent=[x_lim[0], x_lim[1], y_lim[0], y_lim[1]],
                       origin='lower', aspect='auto', alpha=0.4, interpolation='nearest')

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                self.parameters[0], self.parameters[0]))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                self.parameters[1], self.parameters[1]))

    # def get_limits(self, axis_limits):
    #     default_x_lim = [-1, 1] if self.scale[0] == 'Tanh' else [0, 1]
    #     default_y_lim = [-1, 1] if self.scale[1] == 'Tanh' else [0, 1]

    #     x_lim = self.x_lim or axis_limits.get(
    #         'x', default_x_lim)
    #     y_lim = self.y_lim or axis_limits.get(
    #         'y', default_y_lim)

    #     return x_lim, y_lim


@Plotter.plot_type("Clustering: Degree of Membership")
class plot_clustering_degree_of_membership(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str], clustering_settings: dict = {},
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, resolution: int = 100):
        self.parameters = tuple(parameters)
        self.clustering_settings = clustering_settings
        if 'clustering_parameters' not in self.clustering_settings:
            self.clustering_settings['clustering_parameters'] = self.parameters

        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.resolution = resolution

        # self.data_key = Interface.request_to_tuple(
        #     self.get_dynamic_plot_requests()[0])

    def get_dynamic_plot_requests(self):
        return [{'method': 'get_clustering', 'settings': {'parameters': self.parameters, 'scale': self.scale, 'clustering_settings': self.clustering_settings}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        x_lim, y_lim = self.get_limits(axis_limits)
        clustering = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]

        xx, yy = np.meshgrid(
            np.linspace(x_lim[0], x_lim[1], self.resolution), np.linspace(
                y_lim[0], y_lim[1], self.resolution)
        )

        mesh_points = np.c_[xx.ravel(), yy.ravel()]
        mesh_points_scaled = np.array(mesh_points)
        if self.scale[0] == 'Tanh':
            mesh_points_scaled[:, 0] = np.arctanh(mesh_points_scaled[:, 0])
        if self.scale[1] == 'Tanh':
            mesh_points_scaled[:, 1] = np.arctanh(mesh_points_scaled[:, 1])

        Z = np.array(clustering.degree_of_membership(mesh_points_scaled))
        Z = Z.max(axis=0)
        Z = Z.reshape(xx.shape)

        ax.contourf(xx, yy, Z, alpha=0.5,
                    levels=np.linspace(0, 1, 11), cmap='coolwarm')

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                self.parameters[0], self.parameters[0]))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                self.parameters[1], self.parameters[1]))

    # def get_limits(self, axis_limits):
    #     default_x_lim = [-1, 1] if self.scale[0] == 'Tanh' else [0, 1]
    #     default_y_lim = [-1, 1] if self.scale[1] == 'Tanh' else [0, 1]

    #     x_lim = self.x_lim or axis_limits.get(
    #         'x', default_x_lim)
    #     y_lim = self.y_lim or axis_limits.get(
    #         'y', default_y_lim)

    #     return x_lim, y_lim


@Plotter.plot_type("Clustering: sns")
class plot_clustering_sns(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str], clustering_settings: dict = {},
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, resolution: int = 100):
        self.parameters = tuple(parameters)
        self.clustering_settings = clustering_settings
        if 'clustering_parameters' not in self.clustering_settings:
            self.clustering_settings['clustering_parameters'] = self.parameters

        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.resolution = resolution

        # self.data_key = Interface.request_to_tuple(
        #     self.get_dynamic_plot_requests()[0])

    def get_dynamic_plot_requests(self):
        return [{'method': 'get_clustering', 'settings': {'parameters': self.parameters, 'scale': self.scale, 'clustering_settings': self.clustering_settings}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        x_lim, y_lim = self.get_limits(axis_limits)
        clustering = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]

        xx, yy = np.meshgrid(
            np.linspace(x_lim[0], x_lim[1], self.resolution), np.linspace(
                y_lim[0], y_lim[1], self.resolution)
        )

        mesh_points = np.c_[xx.ravel(), yy.ravel()]
        mesh_points_scaled = np.array(mesh_points)
        if self.scale[0] == 'Tanh':
            mesh_points_scaled[:, 0] = np.arctanh(mesh_points_scaled[:, 0])
        if self.scale[1] == 'Tanh':
            mesh_points_scaled[:, 1] = np.arctanh(mesh_points_scaled[:, 1])

        Z = np.array(clustering.degree_of_membership(mesh_points_scaled))
        Z = Z.reshape(-1, *xx.shape)
        Z_index = Z.argmax(axis=0)
        Z_flat = Z.max(axis=0).ravel()

        xx_flat = xx.ravel()
        yy_flat = yy.ravel()
        Z_index_flat = Z_index.ravel()

        sns.kdeplot(
            ax=ax,
            x=xx_flat,
            y=yy_flat,
            hue=Z_index_flat,
            weights=Z_flat,
            levels=5,
            thresh=0.5,
            alpha=0.5,
            cmap="mako"
        )

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                self.parameters[0], self.parameters[0]))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                self.parameters[1], self.parameters[1]))

    # def get_limits(self, axis_limits):
    #     default_x_lim = [-1, 1] if self.scale[0] == 'Tanh' else [0, 1]
    #     default_y_lim = [-1, 1] if self.scale[1] == 'Tanh' else [0, 1]

    #     x_lim = self.x_lim or axis_limits.get('x', default_x_lim)
    #     y_lim = self.y_lim or axis_limits.get('y', default_y_lim)

    #     return x_lim, y_lim

# Needs to be fixed!


@Plotter.plot_type("Draw")
class draw(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: Union[tuple[str], None] = None,
                 pos: Optional[Dict[Union[int, str], tuple]] = None,
                 node_attributes: str = "opinion",
                 edge_attributes: str = 'importance',
                 node_info_mode: str = 'none',
                 use_node_color: bool = True,
                 use_edge_thickness: bool = True,
                 show_edge_influences: bool = False,
                 node_size_multiplier: int = 200,
                 arrowhead_length: float = 0.2,
                 arrowhead_width: float = 0.2,
                 min_line_width: float = 0.1,
                 max_line_width: float = 3.0,
                 seed: Optional[int] = None):
        self.parameters = tuple(parameters or ())

        self.pos = pos
        self.node_attributes = node_attributes
        self.edge_attributes = edge_attributes
        self.node_info_mode = node_info_mode
        self.use_node_color = use_node_color
        self.use_edge_thickness = use_edge_thickness
        self.show_edge_influences = show_edge_influences
        self.node_size_multiplier = node_size_multiplier
        self.arrowhead_length = arrowhead_length
        self.arrowhead_width = arrowhead_width
        self.min_line_width = min_line_width
        self.max_line_width = max_line_width
        self.seed = seed

        # self.data_key = Interface.request_to_tuple(
        #     self.get_dynamic_plot_requests()[0])

        self._x_lim = None
        self._y_lim = None

    def get_dynamic_plot_requests(self):
        return [{'method': 'get_mean_graph', 'settings': {}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        # Fetch the HariGraph instance using the data_key
        image = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]

        # Use the specified or default positions for nodes
        self.pos = self.pos or image.position_nodes(seed=self.seed)

        # Prepare Node Labels
        node_labels = self._prepare_node_labels(image)

        # Prepare Node Colors
        node_colors = self._prepare_node_colors(image, self.use_node_color)

        # Prepare Edge Widths and Labels
        edge_widths, edge_labels = self._prepare_edge_attributes(image)

        # Calculate Node Sizes
        node_sizes = self._calculate_node_sizes(image)

        # Draw Nodes
        nx.draw_networkx_nodes(
            image, self.pos, node_color=node_colors, node_size=node_sizes, ax=ax)

        # Draw Edges
        self._draw_edges(image, ax, edge_widths)

        # Draw Labels
        nx.draw_networkx_labels(image, self.pos, labels=node_labels, ax=ax)
        if self.show_edge_influences and edge_labels:
            nx.draw_networkx_edge_labels(
                image, self.pos, edge_labels=edge_labels, ax=ax)

    def _prepare_node_labels(self, image):
        node_labels = {}
        match self.node_info_mode:
            case 'opinion':
                node_labels = {node: f"{opinion:.2f}" for node, opinion in image.gatherer.gather(
                    self.node_attributes).items()}
            case 'ids':
                node_labels = {node: str(node) for node in image.nodes()}
            case 'labels':
                node_labels = {node: ','.join(
                    map(str, label)) for node, label in image.gatherer.gather("Label").items()}
            case 'cluster_size':
                node_labels = {node: str(
                    len(label)) for node, label in image.gatherer.gather("Label").items()}
        return node_labels

    def _prepare_node_colors(self, image, use_node_color):
        node_colors = []
        default_color = 'lightblue'  # Default color for nodes without specified colors
        for node in image.nodes():
            if use_node_color:
                color = cm.bwr(image.gatherer.gather(
                    self.node_attributes).get(node, 0.5))
            else:
                color = default_color
            node_colors.append(color)
        return node_colors

    def _prepare_edge_attributes(self, image):
        edge_weights = list(image.gatherer.gather(
            self.edge_attributes).values())
        scaled_weights = np.sqrt(edge_weights)  # Non-linear scaling
        max_scaled_weight = np.max(scaled_weights)
        min_scaled_weight = np.min(scaled_weights)
        edge_widths = [(self.min_line_width + (self.max_line_width - self.min_line_width) * (weight -
                        min_scaled_weight) / (max_scaled_weight - min_scaled_weight)) for weight in scaled_weights]
        edge_labels = {(u, v): f"{influence:.2f}" for (u, v), influence in image.gatherer.gather(
            self.edge_attributes).items()} if self.show_edge_influences else None
        return edge_widths, edge_labels

    def _calculate_node_sizes(self, image):
        node_sizes = []
        # Default size for nodes without labels
        default_size = self.node_size_multiplier
        for node in image.nodes():
            label = image.nodes[node].get('Label')
            if label:
                size = self.node_size_multiplier * \
                    math.sqrt(len(label))  # Nonlinear scaling
            else:
                size = default_size
            node_sizes.append(size)
        return node_sizes

    def _draw_edges(self, image, ax, edge_widths):
        # Initialize style with a default value
        default_style = 'arc3,rad=0.3'  # or any other default style you prefer

        for (u, v), width in zip(image.edges(), edge_widths):
            # Here you might have some logic to determine the style for each edge
            # For example:
            # if some_condition:
            #     style = 'some_specific_style'
            # else:
            #     style = default_style

            # If no specific style is set, use the default
            style = default_style

            # Now draw the edge with the defined style
            nx.draw_networkx_edges(image, self.pos, edgelist=[(u, v)], width=width, ax=ax,
                                   arrowstyle=f'-|>,head_length={self.arrowhead_length},head_width={self.arrowhead_width}',
                                   connectionstyle=style)


@Plotter.plot_type("Static: Time line")
class plot_time_line(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str],
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None):
        self.parameters = tuple(parameters)
        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim

        # self.data_key = Interface.request_to_tuple(
        #     self.get_dynamic_plot_requests()[0])

    def get_dynamic_plot_requests(self):
        return [{'method': 'mean_time', 'settings': {}}]

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: dict, axis_limits: dict):
        x_lim, y_lim = self.get_limits(axis_limits)

        data = dynamic_data_cache[self.get_dynamic_plot_requests()[0]]

        x_parameter, y_parameter = self.parameters

        if x_parameter == 'Time':
            # Time is on the x-axis, draw a vertical line
            ax.axvline(x=data, color='r', linestyle='--')
        elif y_parameter == 'Time':
            # Time is on the y-axis, draw a horizontal line
            ax.axhline(y=data, color='r', linestyle='--')

        if x_lim is not None:
            ax.set_xlim(*x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                x_parameter, x_parameter))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                y_parameter, y_parameter))


@Plotter.plot_type("Static: Node lines")
class plot_node_lines(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str],
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, colormap: str = 'coolwarm'):
        self.parameters = tuple(parameters)
        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.colormap = colormap

        self._static_data = None

        # self.data_key = Interface.request_to_tuple(
        #     self.get_static_plot_requests()[0])

    def get_static_plot_requests(self):
        return [{'method': 'calculate_node_values', 'settings': {'parameters': self.parameters, 'scale': self.scale}}]

    def data(self, static_data_cache: List[dict]):
        if self._static_data is not None:
            return self._static_data

        data_list = static_data_cache[self.get_static_plot_requests()[0]]
        self._static_data = self.transform_data(data_list)
        return self._static_data

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: List[dict], axis_limits: dict):

        x_lim, y_lim = self.get_limits(axis_limits)

        data = self.data(static_data_cache)

        # print(f'{data = }')
        # print(f'{data = }')
        # print(f'{data.keys() = }')
        # print(f'{data["Time"] = }')

        x_parameter, y_parameter = self.parameters

        if not (x_parameter == 'Time' or y_parameter == 'Time'):
            raise ValueError('One of the parameters should be Time.')

        # Determine which axis time is on
        time_is_x_axis = x_parameter == 'Time'

        x_values = data[x_parameter]
        y_values = data[y_parameter]

        if self.scale[0 if time_is_x_axis else 1] == 'Tanh':
            x_values = np.tanh(x_values)
        if self.scale[1 if time_is_x_axis else 0] == 'Tanh':
            y_values = np.tanh(y_values)

        # Color map for final state values
        cmap = plt.get_cmap(self.colormap)
        final_values = y_values[:, -1] if time_is_x_axis else x_values[:, -1]
        colors = cmap(final_values / max(final_values))

        # Plotting
        for i, color in enumerate(colors):
            if time_is_x_axis:
                ax.plot(x_values, y_values[i], color=color)
            else:
                ax.plot(y_values[i], x_values, color=color)

        # Set limits
        if x_lim is not None:
            ax.set_xlim(*x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                self.parameters[0], self.parameters[0]))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                self.parameters[1], self.parameters[1]))


@Plotter.plot_type("Static: Graph line")
class plot_graph_line(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str],
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None, function: str = 'mean'):
        self.parameters = tuple(parameters)
        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.function = function

        self._static_data = None

        # self.data_key = Interface.request_to_tuple(
        #     self.get_static_plot_requests()[0])

    def get_static_plot_requests(self):
        return [{'method': 'calculate_function_of_node_values', 'settings': {'parameters': self.parameters, 'scale': self.scale, 'function': self.function}}]

    def data(self, static_data_cache: List[dict]):
        if self._static_data is not None:
            return self._static_data

        data = static_data_cache[self.get_static_plot_requests()[0]]

        keys = list(data[0].keys())

        self._static_data = {key: [] for key in keys}
        for frame in data:
            for key in keys:
                self._static_data[key].append(frame[key])

        return self._static_data

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: List[dict], axis_limits: dict):
        x_lim, y_lim = self.get_limits(axis_limits)

        data = self.data(static_data_cache)

        x_parameter, y_parameter = self.parameters

        x_values = data[x_parameter]
        y_values = data[y_parameter]

        if self.scale[0] == 'Tanh':
            x_values = np.tanh(x_values)
        if self.scale[1] == 'Tanh':
            y_values = np.tanh(y_values)

        ax.plot(x_values, y_values)

        if x_lim is not None:
            ax.set_xlim(*x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                x_parameter, x_parameter))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                y_parameter, y_parameter))


@Plotter.plot_type("Static: Graph Range")
class plot_fill_between(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str], functions: Optional[List[str]] = None,
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None):
        self.parameters = tuple(parameters)
        self.functions = functions or ['min', 'max']
        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim

        self._static_data = None

        # Generate data keys for both functions
        self.data_key_min = Interface.request_to_tuple(
            self.get_static_plot_requests()[0])
        self.data_key_max = Interface.request_to_tuple(
            self.get_static_plot_requests()[1])

    def get_static_plot_requests(self):
        return [
            {'method': 'calculate_function_of_node_values', 'settings': {
                'parameters': self.parameters, 'scale': self.scale, 'function': self.functions[0]}},
            {'method': 'calculate_function_of_node_values', 'settings': {
                'parameters': self.parameters, 'scale': self.scale, 'function': self.functions[1]}}
        ]

    def data(self, static_data_cache: List[dict], function_key):
        data = static_data_cache[function_key]

        keys = list(data[0].keys())

        _static_data = {key: [] for key in keys}
        for frame in data:
            for key in keys:
                _static_data[key].append(frame[key])

        return _static_data

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: List[dict], axis_limits: dict):
        x_lim, y_lim = self.get_limits(axis_limits)

        data_min = self.data(static_data_cache, self.data_key_min)
        data_max = self.data(static_data_cache, self.data_key_max)

        x_parameter, y_parameter = self.parameters

        x_values = data_min[x_parameter]
        y_values_min = data_min[y_parameter]
        y_values_max = data_max[y_parameter]

        if self.scale[0] == 'Tanh':
            x_values = np.tanh(x_values)
        if self.scale[1] == 'Tanh':
            y_values_min = np.tanh(y_values_min)
            y_values_max = np.tanh(y_values_max)

        # Fill the area between the min and max curves
        ax.fill_between(x_values, y_values_min, y_values_max, alpha=0.5)

        if x_lim is not None:
            ax.set_xlim(*x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                x_parameter, x_parameter))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                y_parameter, y_parameter))


@Plotter.plot_type("Static: Clustering Line")
class plot_clustering_line(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str], clustering_settings: dict = {},
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None):
        self.parameters = tuple(parameters)
        self.clustering_settings = clustering_settings
        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim

        self._static_data = None

        # self.data_key = Interface.request_to_tuple(
        #     self.get_static_plot_requests()[0])

    def get_static_plot_requests(self):
        return [{'method': 'clustering_graph_values', 'settings': {'parameters': self.parameters, 'scale': self.scale, 'clustering_settings': self.clustering_settings}}]

    def data(self, static_data_cache: List[dict]):
        if self._static_data is not None:
            return self._static_data

        data = static_data_cache[self.get_static_plot_requests()[0]]

        data = self.transform_data(data)

        x_parameter, y_parameter = self.parameters

        # Transform data to suitable format for plotting
        x_values = np.array(data[x_parameter])
        y_values = np.array(data[y_parameter])

        if self.scale[0] == 'Tanh':
            x_values = np.tanh(x_values)
        if self.scale[1] == 'Tanh':
            y_values = np.tanh(y_values)

        self._static_data = {'x': x_values, 'y': y_values}
        return self._static_data

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: List[dict], axis_limits: dict):
        x_lim, y_lim = self.get_limits(axis_limits)

        data = self.data(static_data_cache)

        # print(f'{data = }')

        ax.plot(data['x'], data['y'].T)

        if x_lim is not None:
            ax.set_xlim(*x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                self.parameters[0], self.parameters[0]))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                self.parameters[1], self.parameters[1]))


@Plotter.plot_type("Static: Clustering Range")
class plot_fill_between_clustering(Plot):
    def __init__(self, color_scheme: ColorScheme, parameters: tuple[str], clustering_settings: dict = {},
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None):
        assert len(
            parameters) == 3, "Three parameters are required, with the last or first being 'Time'."

        self.parameters = tuple(parameters)
        self.clustering_settings = clustering_settings
        self.scale = tuple(scale or ('Linear', 'Linear'))
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim

        self._static_data = None

        # self.data_key = Interface.request_to_tuple(
        #     self.get_static_plot_requests()[0])

    def get_static_plot_requests(self):
        return [{'method': 'clustering_graph_values', 'settings': {'parameters': self.parameters, 'scale': self.scale, 'clustering_settings': self.clustering_settings}}]

    def data(self, static_data_cache: List[dict]):
        if self._static_data is not None:
            return self._static_data

        data = static_data_cache[self.get_static_plot_requests()[0]]

        data = self.transform_data(data)

        x_parameter, y1_parameter, y2_parameter = self.parameters

        # Transform data to suitable format for plotting
        x_values = np.array(data[x_parameter])
        y1_values = np.array(data[y1_parameter])
        y2_values = np.array(data[y2_parameter])

        if self.scale[0] == 'Tanh':
            x_values = np.tanh(x_values)
        if self.scale[1] == 'Tanh':
            y1_values = np.tanh(y1_values)
            y2_values = np.tanh(y2_values)

        self._static_data = {'x': x_values, 'y1': y1_values, 'y2': y2_values}
        return self._static_data

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: List[dict], axis_limits: dict):
        x_lim, y_lim = self.get_limits(axis_limits)

        data = self.data(static_data_cache)

        # Assuming x_values are common for all intervals
        x_values = data['x']

        # Iterate over each set of intervals
        # Assuming data['y1'] and data['y2'] have the same first dimension
        for i in range(data['y1'].shape[0]):
            y1_values = data['y1'][i, :]
            y2_values = data['y2'][i, :]

            # Use tanh scaling if specified
            if self.scale[1] == 'Tanh':
                y1_values = np.tanh(y1_values)
                y2_values = np.tanh(y2_values)

            # Fill the area between y1 and y2 for this set of intervals
            ax.fill_between(x_values, y1_values, y2_values, alpha=0.5)

        # Setting x and y limits if provided
        if x_lim is not None:
            ax.set_xlim(*x_lim)
        if y_lim is not None:
            ax.set_ylim(*y_lim)

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        # Setting labels
        if self.show_x_label:
            ax.set_xlabel(Plotter._parameter_dict.get(
                self.parameters[0], self.parameters[0]))
        if self.show_y_label:
            ax.set_ylabel(Plotter._parameter_dict.get(
                self.parameters[1], self.parameters[1]))


@Plotter.plot_type("Static: Opinions")
class plot_opinions(Plot):
    def __init__(self, color_scheme: ColorScheme, clustering_settings: dict = {},
                 scale: Optional[Tuple[str] | None] = None,
                 show_x_label: bool = True, show_y_label: bool = True,
                 x_lim: Optional[Sequence[float] | None] = None, y_lim: Optional[Sequence[float] | None] = None,
                 min_cluster_size: int = 2, colormap: str = 'coolwarm', show_colorbar: bool = False, show_legend: bool = True):
        self.parameters = ('Time', 'Opinion')
        self.clustering_settings = clustering_settings
        self.scale = scale or tuple('Linear', 'Linear')
        self.show_x_label = show_x_label
        self.show_y_label = show_y_label
        self._x_lim = x_lim
        self._y_lim = y_lim
        self.min_cluster_size = min_cluster_size
        self.colormap = colormap

        self.show_colorbar = show_colorbar
        self.show_legend = show_legend

        self._static_data = None
        # self.data_key = Interface.request_to_tuple(
        #     self.get_static_plot_requests()[0])
        self.max_value = None
        self.min_value = None

    def get_static_plot_requests(self):
        return [{'method': 'clustering_graph_values', 'settings': {'parameters': ('Time', 'Min opinion', 'Opinion', 'Max opinion', 'Cluster size', 'Label'), 'scale': self.scale, 'clustering_settings': self.clustering_settings}}]

    def get_track_clusterings_requests(self):
        return [self.clustering_settings]

    def data(self, static_data_cache: List[dict]) -> dict:
        if self._static_data is not None:
            return self._static_data

        data = static_data_cache[self.get_static_plot_requests()[0]]

        data = self.transform_data(data, transform_parameter='Label')
        # print(f'{data = }')

        # Transform data to suitable format for plotting
        time = np.array(data['Time'])
        labels = data['Label']
        min_opinion = np.array(data['Min opinion'])
        opinion = np.array(data['Opinion'])
        max_opinion = np.array(data['Max opinion'])
        cluster_size = np.array(data['Cluster size'])

        if self.scale[0] == 'Tanh':
            x_values = np.tanh(x_values)
        if self.scale[1] == 'Tanh':
            min_opinion = np.tanh(min_opinion)
            opinion = np.tanh(opinion)
            max_opinion = np.tanh(max_opinion)

        self.min_value = np.nanmin(min_opinion)
        self.max_value = np.nanmax(max_opinion)

        self._static_data = {'Time': time, 'Label': labels, 'Min opinion': min_opinion,
                             'Opinion': opinion, 'Max opinion': max_opinion, 'Cluster size': cluster_size}
        return self._static_data

    def plot(self, ax: plt.Axes, dynamic_data_cache: dict, static_data_cache: List[dict], axis_limits: dict):
        data = self.data(static_data_cache)
        x_lim, y_lim = self.get_limits(axis_limits)

        time = data['Time']
        labels = data['Label']
        min_opinions = data['Min opinion']
        opinions = data['Opinion']
        max_opinions = data['Max opinion']
        cluster_sizes = data['Cluster size']

        # print(f'{cluster_sizes.shape = }')

        # Filter clusters by size
        valid_clusters = np.any(cluster_sizes >= self.min_cluster_size, axis=1)

        # Define a colormap
        cmap = plt.get_cmap(self.colormap)
        norm = plt.Normalize(np.nanmin(
            opinions[valid_clusters, -1]), np.nanmax(opinions[valid_clusters, -1]))

        for i, valid in enumerate(valid_clusters):
            if valid:
                # Color by the final opinion value
                color = cmap(norm(opinions[i, -1]))

                # Plot the mean opinion line for each valid cluster
                ax.plot(
                    time, opinions[i], label=f'{labels[i]}', color=color)

                # Fill the area between min and max opinions for each valid cluster
                ax.fill_between(time, min_opinions[i], max_opinions[i],
                                color=color, alpha=0.3)

        # Set the x and y axis labels
        if self.show_x_label:
            ax.set_xlabel('Time')
        if self.show_y_label:
            ax.set_ylabel('Opinion')

        # Set the x and y axis limits if provided
        ax.set_xlim(0, np.max(time))
        ax.set_ylim(y_lim)

        Plotter.tanh_axis_labels(ax=ax, scale=self.scale)

        if self.show_colorbar:
            # Add a colorbar to indicate the mapping of the final opinion values to colors
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            ax.figure.colorbar(sm, ax=ax, label='Final Opinion')

        # Optional: Show legend to identify clusters
        if self.show_legend:
            ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
