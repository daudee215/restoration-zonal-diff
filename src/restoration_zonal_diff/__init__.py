"""restoration-zonal-diff: streaming Monte Carlo zonal-diff for restoration scenarios."""

from restoration_zonal_diff.coefficients import CoefficientTable
from restoration_zonal_diff.diff import diff_scenarios
from restoration_zonal_diff.montecarlo import triangular_draws
from restoration_zonal_diff.streamer import accumulate_window, finalize

__all__ = [
    "CoefficientTable",
    "accumulate_window",
    "diff_scenarios",
    "finalize",
    "triangular_draws",
]

__version__ = "0.1.0"
