from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Dict
from typing import List

import numpy as np
import xarray as xr

from glotaran.model.item import model_item
from glotaran.model.item import model_item_typed
from glotaran.model.util import get_subtype
from glotaran.model.util import is_mapping_type
from glotaran.model.util import is_sequence_type
from glotaran.plugin_system.megacomplex_registration import register_megacomplex

if TYPE_CHECKING:
    from typing import Any

    from glotaran.model import DatasetModel


def create_model_megacomplex_type(
    megacomplex_types: dict[str, Megacomplex], default_type: str = None
) -> type:
    @model_item_typed(types=megacomplex_types, default_type=default_type)
    class ModelMegacomplex:
        """This class holds all Megacomplex types defined by a model."""

    return ModelMegacomplex


def megacomplex(
    *,
    dimension: str | None = None,
    model_items: dict[str, dict[str, Any]] = None,
    properties: Any | dict[str, dict[str, Any]] = None,
    dataset_model_items: dict[str, dict[str, Any]] = None,
    dataset_properties: Any | dict[str, dict[str, Any]] = None,
    unique: bool = False,
    exclusive: bool = False,
    register_as: str | None = None,
):
    """The `@megacomplex` decorator is intended to be used on subclasses of
    :class:`glotaran.model.Megacomplex`. It registers the megacomplex model
    and makes it available in analysis models.
    """
    properties = properties if properties is not None else {}
    properties["dimension"] = {"type": str}
    if dimension is not None:
        properties["dimension"]["default"] = dimension

    if model_items is None:
        model_items = {}
    else:
        model_items, properties = _add_model_items_to_properties(model_items, properties)

    dataset_properties = dataset_properties if dataset_properties is not None else {}
    if dataset_model_items is None:
        dataset_model_items = {}
    else:
        dataset_model_items, dataset_properties = _add_model_items_to_properties(
            dataset_model_items, dataset_properties
        )

    def decorator(cls):

        setattr(cls, "_glotaran_megacomplex_model_items", model_items)
        setattr(cls, "_glotaran_megacomplex_dataset_model_items", dataset_model_items)
        setattr(cls, "_glotaran_megacomplex_dataset_properties", dataset_properties)
        setattr(cls, "_glotaran_megacomplex_unique", unique)
        setattr(cls, "_glotaran_megacomplex_exclusive", exclusive)

        megacomplex_type = model_item(properties=properties, has_type=True)(cls)

        if register_as is not None:
            megacomplex_type.name = register_as
            register_megacomplex(register_as, megacomplex_type)

        return megacomplex_type

    return decorator


def _add_model_items_to_properties(model_items: dict, properties: dict) -> tuple[dict, dict]:
    for name, item in model_items.items():
        item_type = item["type"] if isinstance(item, dict) else item
        property_type = str

        if is_sequence_type(item_type):
            property_type = List[str]
            item_type = get_subtype(item_type)
        elif is_mapping_type(item_type):
            property_type = Dict[str, str]
            item_type = get_subtype(item_type)

        property_dict = item.copy() if isinstance(item, dict) else {}
        property_dict["type"] = property_type
        properties[name] = property_dict
        model_items[name] = item_type
    return model_items, properties


class Megacomplex:
    """A base class for megacomplex models.

    Subclasses must overwrite :method:`glotaran.model.Megacomplex.calculate_matrix`
    and :method:`glotaran.model.Megacomplex.index_dependent`.
    """

    def calculate_matrix(
        self,
        dataset_model: DatasetModel,
        global_index: int | None,
        global_axis: np.typing.ArrayLike,
        model_axis: np.typing.ArrayLike,
        **kwargs,
    ) -> xr.DataArray:
        raise NotImplementedError

    def index_dependent(self, dataset_model: DatasetModel) -> bool:
        raise NotImplementedError

    def finalize_data(
        self,
        dataset_model: DatasetModel,
        dataset: xr.Dataset,
        is_full_model: bool = False,
        as_global: bool = False,
    ):
        raise NotImplementedError

    @classmethod
    def glotaran_model_items(cls) -> str:
        return cls._glotaran_megacomplex_model_items

    @classmethod
    def glotaran_dataset_model_items(cls) -> str:
        return cls._glotaran_megacomplex_dataset_model_items

    @classmethod
    def glotaran_dataset_properties(cls) -> str:
        return cls._glotaran_megacomplex_dataset_properties

    @classmethod
    def glotaran_unique(cls) -> bool:
        return cls._glotaran_megacomplex_unique

    @classmethod
    def glotaran_exclusive(cls) -> bool:
        return cls._glotaran_megacomplex_exclusive
