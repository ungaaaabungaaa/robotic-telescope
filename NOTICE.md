# Sources and rights

New application code and computed examples use the repository MIT license. Third-party libraries and data retain their respective licenses; this repository does not relicense Astropy, ERFA, Matplotlib, NumPy, IERS data, or catalog sources.

The astronomy engine is [Astropy](https://www.astropy.org/), with [ERFA](https://github.com/liberfa/erfa) through PyERFA and pinned [astropy-iers-data](https://github.com/astropy/astropy-iers-data). Source/data package versions, IERS file hash/status/range, and the active ERFA leap-second table are recorded in every astronomical report. These packages are dependencies, not vendored copies of their code or tables.

M31/M33 coordinate constants and the M33 reference example are credited to the official Astropy documentation. The M42 H II-region centroid is credited to the [SIMBAD database operated at CDS, Strasbourg](https://simbad.unistra.fr/simbad/sim-id?Ident=M42). Exact example sources are in `docs/method.md` and the bundled request. No external astronomical photographs or catalog bulk data are included.

The previous Bootstrap tutorial remains only in preserved Git history. No old code or imagery was reused. The generated cover's separate prompt/reference/approval provenance is in `docs/images/cover-provenance.json`; it is concept art, not a telescope photograph or physical acceptance record.
