"""
src/ui — Phase 4: Interactive 3D Visualization

Pure rendering modules (no Streamlit imports) that produce Plotly / matplotlib
figures.  The Streamlit app (app.py) imports these and wires them to widgets.

Modules
-------
viewer3d            : 3D tumour surface mesh rendering via marching cubes + Plotly.
mpr_viewer          : Multi-planar reconstruction (axial/sagittal/coronal) slices.
longitudinal_chart  : Plotly timeline chart for tumour volume trends + RANO bands.
uncertainty_viewer  : Entropy / Grad-CAM heatmap overlay on MRI slices.
"""
