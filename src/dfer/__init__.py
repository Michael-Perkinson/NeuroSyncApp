"""DFer/PFer raw photometry analysis.

This package ports the Argotech/Tussock Innovation DFer_v1.4 + PFer_2.4
analysis workflow (OCT-2024). That workflow is based on analysis methods from
GuPPy:

Sherathiya, V. N., Schaid, M. D., Seiler, J. L., Lopez, G. C., & Lerner, T. N.
GuPPy, a Python toolbox for the analysis of fiber photometry data.
Scientific Reports 11, 24212 (2021). https://doi.org/10.1038/s41598-021-03626-9
"""

from .analysis import compute_options, run_analysis
from .pfer import run_pfer

__all__ = ["run_analysis", "run_pfer", "compute_options"]
