import json
import os
import math
from pathlib import Path
from agent.utils import remover_acentos, parse_time, is_time_in_range

# Carregamento Lazy da base de dados
_restaurantes_data = None

def get_restaurantes():
    global _restaurantes_data
    if _restaurantes_data is None:
        file_path = Path(__file__).parent.parent / "restaurantes_bh.json"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                _restaurantes_data = json.load(f)
        except Exception as e:
            print(f"Erro ao carregar {file_path}: {e}")
            _restaurantes_data = []
    return _restaurantes_data

def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    """Calcula a distância em km entre dois pontos via Fórmula de Haversine"""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    
    R = 6371.0 # Raio da terra em km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def buscar_restaurantes(bairro: str = None, cozinha: str = None, lat_usuario: float = None, lon_usuario: float = None):
    """
    Busca restaurantes ativos no Duo Gourmet aplicando filtros e retornando os melhores.
    """
    db = get_restaurantes()
    resultados = []
    
    bairro_norm = remover_acentos(bairro) if bairro else None
    cozinha_norm = remover_acentos(cozinha) if cozinha else None
    
    for r in db:
        if r.get("google_business_status") != "OPERATIONAL":
            continue
            
        r_bairro = remover_acentos(r.get("neighborhood", ""))
        r_cozinha = remover_acentos(r.get("cuisine", ""))
        
        # Filtro de Bairro (busca parcial)
        if bairro_norm and bairro_norm not in r_bairro:
            continue
            
        # Filtro de Cozinha (busca parcial)
        if cozinha_norm and cozinha_norm not in r_cozinha:
            continue
            
        # Calcular distância se GPS fornecido
        r_lat = r.get("lat") or r.get("google_lat")
        r_lon = r.get("lon") or r.get("google_lng")
        
        distancia = float('inf')
        if lat_usuario and lon_usuario and r_lat and r_lon:
            distancia = calcular_distancia_haversine(lat_usuario, lon_usuario, r_lat, r_lon)
            
        # Formatando retorno reduzido para economizar tokens
        resultados.append({
            "name": r.get("name"),
            "neighborhood": r.get("neighborhood"),
            "cuisine": r.get("cuisine"),
            "rating": r.get("google_rating"),
            "distance_km": round(distancia, 2) if distancia != float('inf') else None
        })
        
    # Ordenação: Prioridade para distância (se existir), depois por rating
    if lat_usuario and lon_usuario:
        # Sort por distância crescente. Se empatar ou não tiver, usa rating decrescente.
        resultados.sort(key=lambda x: (x["distance_km"] if x["distance_km"] is not None else 9999, -(x["rating"] or 0)))
    else:
        # Sort por rating decrescente apenas
        resultados.sort(key=lambda x: -(x["rating"] or 0))
        
    return resultados[:5]

def verificar_disponibilidade_duo(restaurant_name: str, dia_semana: str, refeicao: str, hora_usuario: str = None):
    """
    Verifica se o benefício do Duo Gourmet é válido para um dia, período e (opcionalmente) horário específico.
    """
    db = get_restaurantes()
    name_norm = remover_acentos(restaurant_name)
    
    # Busca o restaurante exato ou aproximado
    restaurante_alvo = None
    for r in db:
        if remover_acentos(r.get("name", "")) == name_norm:
            restaurante_alvo = r
            break
            
    if not restaurante_alvo:
        return {"disponivel": False, "horario_validacao": None, "mensagem": f"Restaurante '{restaurant_name}' não encontrado."}
        
    schedule = restaurante_alvo.get("schedule", {})
    dia_info = schedule.get(dia_semana, {})
    if not isinstance(dia_info, dict):
         return {"disponivel": False, "horario_validacao": None, "mensagem": "Informação de horário não encontrada."}
         
    horario_faixa = dia_info.get(refeicao)
    
    if horario_faixa is None:
        return {"disponivel": False, "horario_validacao": None, "mensagem": f"Benefício não disponível no {refeicao} de {dia_semana}."}
        
    # Se houver hora do usuário, valida a faixa
    if hora_usuario and isinstance(horario_faixa, str) and "-" in horario_faixa:
        try:
            start_str, end_str = [x.strip() for x in horario_faixa.split("-")]
            start_time = parse_time(start_str)
            end_time = parse_time(end_str)
            check_time = parse_time(hora_usuario)
            
            if start_time and end_time and check_time:
                is_valid = is_time_in_range(check_time, start_time, end_time)
                if not is_valid:
                    return {
                        "disponivel": False, 
                        "horario_validacao": horario_faixa, 
                        "mensagem": f"Benefício disponível de {horario_faixa}, mas você quer ir às {hora_usuario}."
                    }
        except Exception:
            pass # Ignora erros de parse e prossegue confiando na string geral
            
    return {
        "disponivel": True, 
        "horario_validacao": horario_faixa,
        "mensagem": f"Benefício confirmado para {refeicao} de {dia_semana} ({horario_faixa})."
    }

def obter_detalhes_restaurante(restaurant_name: str):
    """
    Retorna os detalhes completos de um restaurante específico.
    """
    db = get_restaurantes()
    name_norm = remover_acentos(restaurant_name)
    
    for r in db:
        if remover_acentos(r.get("name", "")) == name_norm:
            return {
                "name": r.get("name"),
                "cuisine": r.get("cuisine"),
                "neighborhood": r.get("neighborhood"),
                "address": r.get("address"),
                "description": r.get("description"),
                "google_rating": r.get("google_rating"),
                "google_reviews_count": r.get("google_reviews_count"),
                "google_price_level": r.get("google_price_level"),
                "google_maps_url": r.get("google_maps_url"),
                "phone": r.get("phone"),
                "website": r.get("website"),
                "schedule": r.get("schedule")
            }
    return {"erro": "Restaurante não encontrado."}

def listar_cozinhas_disponiveis():
    """
    Retorna uma lista com todas as culinárias disponíveis.
    """
    db = get_restaurantes()
    cozinhas = set()
    for r in db:
        c = r.get("cuisine")
        if c:
            cozinhas.add(c.strip())
    return sorted(list(cozinhas))
