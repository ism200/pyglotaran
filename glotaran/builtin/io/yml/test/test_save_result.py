from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from textwrap import dedent

import pytest
from pandas.testing import assert_frame_equal

from glotaran import __version__
from glotaran.io import load_result
from glotaran.io import save_result
from glotaran.optimization.optimize import optimize
from glotaran.project.result import Result
from glotaran.testing.simulated_data.sequential_spectral_decay import SCHEME


@pytest.fixture(scope="session")
def dummy_result():
    """Dummy result for testing."""
    print(SCHEME.data["dataset_1"])
    scheme = replace(SCHEME, maximum_number_function_evaluations=1)
    yield optimize(scheme, raise_exception=True)


def test_save_result_yml(
    tmp_path: Path,
    dummy_result: Result,
):
    """Check all files exist."""
    expected = dedent(
        f"""\
        number_of_function_evaluations: 1
        success: true
        termination_reason: The maximum number of function evaluations is exceeded.
        glotaran_version: {__version__}
        free_parameter_labels:
        - rates.species_1
        - rates.species_2
        - rates.species_3
        - irf.center
        - irf.width
        scheme: scheme.yml
        initial_parameters: initial_parameters.csv
        optimized_parameters: optimized_parameters.csv
        parameter_history: parameter_history.csv
        optimization_history: optimization_history.csv
        data:
          dataset_1: dataset_1.nc
        """
    )

    result_dir = tmp_path / "testresult"
    result_path = result_dir / "result.yml"
    save_result(result_path=result_path, result=dummy_result)

    assert dummy_result.source_path == result_path.as_posix()

    assert (result_dir / "result.md").exists()
    assert (result_dir / "scheme.yml").exists()
    assert result_path.exists()
    assert (result_dir / "initial_parameters.csv").exists()
    assert (result_dir / "optimized_parameters.csv").exists()
    assert (result_dir / "optimization_history.csv").exists()
    assert (result_dir / "dataset_1.nc").exists()

    # We can't check equality due to numerical fluctuations
    got = result_path.read_text()
    print(got)
    assert expected in got


def test_save_result_yml_roundtrip(tmp_path: Path, dummy_result: Result):
    """Save and reloaded Result should be the same."""
    result_dir = tmp_path / "testresult"
    result_path = result_dir / "result.yml"
    save_result(result_path=result_path, result=dummy_result)
    result_round_tripped = load_result(result_path)

    assert dummy_result.source_path == result_path.as_posix()
    assert result_round_tripped.source_path == result_path.as_posix()

    assert_frame_equal(
        dummy_result.initial_parameters.to_dataframe(),
        result_round_tripped.initial_parameters.to_dataframe(),
    )
    assert_frame_equal(
        dummy_result.optimized_parameters.to_dataframe(),
        result_round_tripped.optimized_parameters.to_dataframe(),
    )
    assert_frame_equal(
        dummy_result.parameter_history.to_dataframe(),
        result_round_tripped.parameter_history.to_dataframe(),
    )
    assert_frame_equal(
        dummy_result.optimization_history.data, result_round_tripped.optimization_history.data
    )
