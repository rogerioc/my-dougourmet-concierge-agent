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

# Declara o componente de fuso horário
_timezone_path = os.path.join(_parent_dir, "timezone_component")
_timezone_detector = components.declare_component("timezone_detector", path=_timezone_path)

def render_timezone_detector(key=None):
    """
    Detecta de forma reativa o fuso horário (timezone) do navegador do usuário.
    """
    return _timezone_detector(key=key)
