import os
import streamlit.components.v1 as components

# Diretório do componente customizado
_parent_dir = os.path.dirname(os.path.abspath(__file__))
_component_path = os.path.join(_parent_dir, "gps_component")

# Declara o componente
_gps_picker = components.declare_component("gps_picker", path=_component_path)

def render_gps_picker(key=None, height=220):
    """
    Renderiza o componente Leaflet de geolocalização e retorna as coordenadas {lat, lon}.
    """
    return _gps_picker(key=key, height=height)
