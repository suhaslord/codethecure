# Data and third-party assets

## BreastMNIST / MedMNIST+

- Distribution: https://zenodo.org/records/10519652
- Official metadata: https://github.com/MedMNIST/MedMNIST/blob/main/medmnist/info.py
- Project: https://medmnist.com/
- Archive: `breastmnist_64.npz`, MD5 `742edef2a1fd1524b2efff4bd7ba9364`.
- License for BreastMNIST: Creative Commons Attribution 4.0, https://creativecommons.org/licenses/by/4.0/.
- Yang, J. et al. MedMNIST v2 — A large-scale lightweight benchmark for 2D and 3D biomedical image classification. Scientific Data 10, 41 (2023). https://doi.org/10.1038/s41597-022-01721-8.
- Al-Dhabyani, W., Gomaa, M., Khaled, H. & Fahmy, A. Dataset of breast ultrasound images. Data in Brief 28, 104863 (2020). https://doi.org/10.1016/j.dib.2019.104863.

GainGuard uses the official 64 × 64 release and split membership. Displayed stressed images are digitally modified derivatives: gain scaling, seeded multiplicative Gaussian noise and/or a synthetic depth-dependent attenuation column. The source images are also resized for browser display. The data authors do not endorse this project. The NPZ is downloaded from the official distribution at runtime and is not checked into this repository.

## Public Sans

Self-hosted Latin variable font from Google Fonts, distributed under the SIL Open Font License 1.1. See `web/fonts/OFL.txt`. Source: https://github.com/google/fonts/tree/main/ofl/publicsans. Font: https://fonts.gstatic.com/s/publicsans/v21/ijwRs572Xtc6ZYQws9YVwnNGfJ4.woff2.

## Methods

- Guo, C., Pleiss, G., Sun, Y. & Weinberger, K. Q. On Calibration of Modern Neural Networks. ICML / PMLR 70 (2017). https://proceedings.mlr.press/v70/guo17a.html.
- MedMNIST-C, a related medical-image corruption benchmark. https://arxiv.org/abs/2406.17536.

PyTorch, NumPy and Pillow are runtime dependencies installed separately, not vendored assets. The wordmark, mark, CSS and chart geometry were created for this prototype. Screenshot/video evidence contains the attributed BreastMNIST images above.
