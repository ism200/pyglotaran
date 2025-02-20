"""Functions for simulating a dataset using a global optimization model."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import xarray as xr

from glotaran.model import DatasetModel
from glotaran.optimization.matrix_provider import MatrixProvider

if TYPE_CHECKING:
    from numpy.typing import ArrayLike

    from glotaran.model import Model
    from glotaran.parameter import ParameterGroup


def simulate(
    model: Model,
    dataset: str,
    parameters: ParameterGroup,
    coordinates: dict[str, ArrayLike],
    clp: xr.DataArray | None = None,
    noise: bool = False,
    noise_std_dev: float = 1.0,
    noise_seed: int | None = None,
) -> xr.Dataset:
    """Simulate a dataset using a model.

    Parameters
    ----------
    model : Model
        The model containing the dataset model.
    dataset : str
        Label of the dataset to simulate
    parameters : ParameterGroup
        The parameters for the simulation, organized in a `ParameterGroup`.
    coordinates : dict[str, ArrayLike]
        A dictionary with the coordinates used for simulation (e.g. time, wavelengths, ...).
    clp : xr.DataArray | None
        A matrix with conditionally linear parameters (e.g. spectra, pixel intensity, ...).
        Will be used instead of the dataset's global megacomplexes if not None.
    noise : bool
        Add noise to the simulation.
    noise_std_dev : float
        The standard deviation for noise simulation.
    noise_seed : int | None
        The seed for the noise simulation.

    Returns
    -------
    xr.Dataset
        The simulated dataset.


    Raises
    ------
    ValueError
        Raised if dataset model has no global megacomplex and no clp are provided.
    """
    dataset_model = model.dataset[dataset].fill(model, parameters)  # type:ignore[attr-defined]
    model_dimension = dataset_model.get_model_dimension()
    model_axis = coordinates[model_dimension]
    global_dimension = next(dim for dim in coordinates if dim != model_dimension)
    global_axis = coordinates[global_dimension]

    if dataset_model.has_global_model():
        result = simulate_full_model(
            dataset_model, global_dimension, global_axis, model_dimension, model_axis
        )
    elif clp is None:
        raise ValueError(
            f"Cannot simulate dataset '{dataset}'. "
            "No global megacomplex is defined and no clp provided."
        )
    else:
        result = simulate_from_clp(
            dataset_model, global_dimension, global_axis, model_dimension, model_axis, clp
        )

    if noise:
        if noise_seed is not None:
            np.random.seed(noise_seed)
        result["data"] = (result.data.dims, np.random.normal(result.data, noise_std_dev))

    return result


def simulate_from_clp(
    dataset_model: DatasetModel,
    global_dimension: str,
    global_axis: ArrayLike,
    model_dimension: str,
    model_axis: ArrayLike,
    clp: xr.DataArray,
) -> xr.Dataset:
    """Simulate a dataset model from pre-defined conditionally linear parameters.

    Parameters
    ----------
    dataset_model : DatasetModel
        The dataset model to simulate.
    global_dimension : str
        The global dimension of the dataset.
    global_axis : ArrayLike
        The global axis of the dataset.
    model_dimension : str
        The model dimension of the dataset.
    model_axis : ArrayLike
        The model axis of the dataset.
    clp : xr.DataArray
        A matrix with conditionally linear parameters.

    Returns
    -------
    xr.Dataset
        The simulated dataset.

    Raises
    ------
    ValueError
        Raised if the clp are missing the dimension 'clp_label'.
    """
    if "clp_label" not in clp.coords:
        raise ValueError("Missing coordinate 'clp_label' in clp.")
    matrices = (
        [
            MatrixProvider.calculate_dataset_matrix(dataset_model, index, global_axis, model_axis)
            for index, _ in enumerate(global_axis)
        ]
        if dataset_model.is_index_dependent()
        else [
            MatrixProvider.calculate_dataset_matrix(dataset_model, None, global_axis, model_axis)
        ]
        * global_axis.size
    )

    result = xr.DataArray(
        np.zeros((model_axis.size, global_axis.size)),
        coords=[
            (model_dimension, model_axis.data),
            (global_dimension, global_axis.data),
        ],
    )
    result = result.to_dataset(name="data")
    for i in range(global_axis.size):
        result.data[:, i] = np.dot(
            matrices[i].matrix,
            clp.isel({global_dimension: i}).sel({"clp_label": matrices[i].clp_labels}),
        )

    return result


def simulate_full_model(
    dataset_model: DatasetModel,
    global_dimension: str,
    global_axis: ArrayLike,
    model_dimension: str,
    model_axis: ArrayLike,
) -> xr.Dataset:
    """Simulate a dataset model with global megacomplexes.

    Parameters
    ----------
    dataset_model : DatasetModel
        The dataset model to simulate.
    global_dimension : str
        The global dimension of the dataset.
    global_axis : ArrayLike
        The global axis of the dataset.
    model_dimension : str
        The model dimension of the dataset.
    model_axis : ArrayLike
        The model axis of the dataset.

    Returns
    -------
    xr.Dataset
        The simulated dataset.

    Raises
    ------
    ValueError
        Raised if at least one of the dataset model's global megacomplexes is index dependent.
    """
    if any(
        m.index_dependent(dataset_model)  # type:ignore[attr-defined]
        for m in dataset_model.global_megacomplex
    ):
        raise ValueError("Index dependent models for global dimension are not supported.")

    global_matrix = MatrixProvider.calculate_dataset_matrix(
        dataset_model, None, global_axis, model_axis, global_matrix=True
    )
    global_clp_labels = global_matrix.clp_labels
    global_matrix = xr.DataArray(
        global_matrix.matrix.T,
        coords=[
            ("clp_label", global_clp_labels),
            (global_dimension, global_axis),
        ],
    )

    return simulate_from_clp(
        dataset_model, global_dimension, global_axis, model_dimension, model_axis, global_matrix
    )
