from os.path import abspath
from os.path import dirname
from os.path import join

import numpy as np
import pytest

from glotaran.builtin.megacomplexes.decay.decay_megacomplex import DecayMegacomplex
from glotaran.builtin.megacomplexes.decay.initial_concentration import InitialConcentration
from glotaran.builtin.megacomplexes.decay.irf import IrfMultiGaussian
from glotaran.builtin.megacomplexes.spectral.shape import SpectralShapeGaussian
from glotaran.io import load_model
from glotaran.model import DatasetModel
from glotaran.model import Model
from glotaran.model import Weight
from glotaran.model.clp_penalties import EqualAreaPenalty
from glotaran.model.constraint import OnlyConstraint
from glotaran.model.constraint import ZeroConstraint
from glotaran.parameter import ParameterGroup

THIS_DIR = dirname(abspath(__file__))


@pytest.fixture
def model():
    spec_path = join(THIS_DIR, "test_model_spec.yml")
    m = load_model(spec_path)
    print(m.markdown())
    return m


def test_correct_model(model):
    assert isinstance(model, Model)
    assert "decay" == model.default_megacomplex
    assert "decay" in model.megacomplex_types
    assert "spectral" in model.megacomplex_types


def test_dataset(model):
    assert len(model.dataset) == 2

    assert "dataset1" in model.dataset
    dataset = model.dataset["dataset1"]
    assert isinstance(dataset, DatasetModel)
    assert dataset.label == "dataset1"
    assert dataset.megacomplex == ["cmplx1"]
    assert dataset.initial_concentration == "inputD1"
    assert dataset.irf == "irf1"
    assert dataset.scale.full_label == "1"

    assert "dataset2" in model.dataset
    dataset = model.dataset["dataset2"]
    assert isinstance(dataset, DatasetModel)
    assert dataset.label == "dataset2"
    assert dataset.megacomplex == ["cmplx2"]
    assert dataset.initial_concentration == "inputD2"
    assert dataset.irf == "irf2"
    assert dataset.scale.full_label == "2"
    assert dataset.spectral_axis_scale == 1e7
    assert dataset.spectral_axis_inverted


def test_constraints(model):
    print(model.clp_constraints)
    assert len(model.clp_constraints) == 2

    zero = model.clp_constraints[0]
    assert isinstance(zero, ZeroConstraint)
    assert zero.target == "s1"
    assert zero.interval == [[1, 100], [2, 200]]

    only = model.clp_constraints[1]
    assert isinstance(only, OnlyConstraint)
    assert only.target == "s1"
    assert only.interval == [[1, 100], [2, 200]]


def test_penalties(model):
    assert len(model.clp_area_penalties) == 1
    assert all(isinstance(c, EqualAreaPenalty) for c in model.clp_area_penalties)
    eac = model.clp_area_penalties[0]
    assert eac.source == "s3"
    assert eac.source_intervals == [[670, 810]]
    assert eac.target == "s2"
    assert eac.target_intervals == [[670, 810]]
    assert eac.parameter.full_label == "55"
    assert eac.weight == 0.0016


def test_relations(model):
    print(model.clp_relations)
    assert len(model.clp_relations) == 1

    rel = model.clp_relations[0]

    assert rel.source == "s1"
    assert rel.target == "s2"
    assert rel.interval == [[1, 100], [2, 200]]


def test_initial_concentration(model):
    assert len(model.initial_concentration) == 2

    for i, _ in enumerate(model.initial_concentration, start=1):
        label = f"inputD{i}"
        assert label in model.initial_concentration
        initial_concentration = model.initial_concentration[label]
        assert initial_concentration.compartments == ["s1", "s2", "s3"]
        assert isinstance(initial_concentration, InitialConcentration)
        assert initial_concentration.label == label
        assert [p.full_label for p in initial_concentration.parameters] == ["1", "2", "3"]


def test_irf(model):
    assert len(model.irf) == 2

    for i, _ in enumerate(model.irf, start=1):
        label = f"irf{i}"
        assert label in model.irf
        irf = model.irf[label]
        assert isinstance(irf, IrfMultiGaussian)
        assert irf.label == label
        want = ["1"] if i == 1 else ["1", "2"]
        assert [p.full_label for p in irf.center] == want
        want = ["2"] if i == 1 else ["3", "4"]
        assert [p.full_label for p in irf.width] == want

        if i == 2:
            want = ["3"] if i == 1 else ["5", "6"]
            assert [p.full_label for p in irf.center_dispersion_coefficients] == want
            want = ["7", "8"]
            assert [p.full_label for p in irf.width_dispersion_coefficients] == want
            want = ["9"]
            assert [p.full_label for p in irf.scale] == want
        assert irf.normalize == (i == 1)

        if i == 2:
            assert irf.backsweep
            assert irf.backsweep_period, 55
        else:
            assert not irf.backsweep
            assert irf.backsweep_period is None


def test_k_matrices(model):
    assert "km1" in model.k_matrix
    parameter = ParameterGroup.from_list([1, 2, 3, 4, 5, 6, 7])
    print(model.k_matrix["km1"].fill(model, parameter).matrix)
    reduced = model.k_matrix["km1"].fill(model, parameter).reduced(["s1", "s2", "s3", "s4"])
    print(parameter)
    print(reduced)
    wanted = np.asarray([[1, 3, 5, 7], [2, 0, 0, 0], [4, 0, 0, 0], [6, 0, 0, 0]])
    print(wanted)
    assert np.array_equal(reduced, wanted)


def test_weight(model):

    weight = model.weights[0]
    assert isinstance(weight, Weight)
    assert weight.datasets == ["d1", "d2"]
    assert weight.global_interval == [100, 102]
    assert weight.model_interval == [301, 502]
    assert weight.value == 42


def test_shapes(model):

    assert "shape1" in model.shape

    shape = model.shape["shape1"]
    assert isinstance(shape, SpectralShapeGaussian)
    assert shape.amplitude.full_label == "shape.1"
    assert shape.location.full_label == "shape.2"
    assert shape.width.full_label == "shape.3"


def test_megacomplexes(model):
    assert len(model.megacomplex) == 3

    for i in range(1, 3):
        label = f"cmplx{i}"
        assert label in model.megacomplex
        megacomplex = model.megacomplex[label]
        assert isinstance(megacomplex, DecayMegacomplex)
        assert megacomplex.label == label
        assert megacomplex.k_matrix == [f"km{i}"]

    assert "cmplx3" in model.megacomplex
    megacomplex = model.megacomplex["cmplx3"]
    assert len(megacomplex.shape) == 2
    assert megacomplex.shape["s1"] == "shape1"
    assert megacomplex.shape["s2"] == "shape2"
