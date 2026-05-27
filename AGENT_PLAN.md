# 🤖 Plan: Restaurant Recommendation Agent — Duo Gourmet

## Overview

Build a conversational AI agent in Python that, based on preferences provided by the user (neighborhood, type of cuisine, day, and period), filters restaurants from the `restaurantes_bh.json` file, validates the availability of the Duo Gourmet benefit, and returns a personalized and well-founded recommendation.

The agent uses **Function Calling** from the Gemini model via `google-genai`, operating in a **ReAct** (Reasoning → Action → Observation) loop until it delivers the final response.

---

## Architecture

```
User
  │
  ▼
[app.py]  ─── prompt + tools ──►  [Gemini API]
                                      │
                               Decides which tool to call
                                      │
                         ◄─── FunctionCall (name + args)
  │
  ▼
[tools.py]  (executes local function on JSON)
  │
  ▼
[Gemini API]  ◄─── FunctionResponse (result)
  │
  ▼
Final text response to the user
```

---

## File Structure

```
MyDuoConcierge/
├── restaurantes_bh.json      # Database source
├── .streamlit/
│   └── config.toml           # Visual theme configuration (DuoList Dark + Gold)
├── agent/
│   ├── __init__.py
│   ├── agent_core.py         # Main agent loop
│   ├── tools.py              # Search functions on the JSON database
│   ├── prompts.py            # System prompt / instructions
│   ├── utils.py              # Helpers (weekday, current time)
│   ├── location_picker.py    # Custom GPS picker component wrapper
│   └── gps_component/        # Folder containing the Leaflet map index.html
└── requirements.txt
```

---

## Phase 1 — Tools (tools.py)

Each function below will be exposed to the model as a "tool" (JSON schema). To ensure reliable searches, we will use **string normalization** (removing accents via `unicodedata` and converting to lowercase) in all neighborhood or cuisine searches.

### `buscar_restaurantes` (search_restaurants)
```
Inputs: neighborhood (str, optional), cuisine (str, optional), user_lat (float, optional), user_lon (float, optional)
Output: list of objects with { name, neighborhood, cuisine, rating, distance_km }

Logic:
  - Loads restaurantes_bh.json.
  - Normalizes search terms (e.g., "Lourdes" -> "lourdes", "Contemporânea" -> "contemporanea").
  - Filters by neighborhood and cuisine using partial searches (e.g., `normalized_neighborhood in normalized_item_neighborhood`).
  - Ensures only active establishments are returned (`google_business_status == "OPERATIONAL"`).
  - If user_lat and user_lon are provided:
    - Calculates the distance in km of each restaurant using the Haversine Formula:
      d = 2 * r * arcsin(sqrt(sin²(Δlat/2) + cos(lat1)*cos(lat2)*sin²(Δlon/2))) where r = 6371.
    - Sorts the list by distance (from closest to farthest).
  - If coordinates are not provided, sorts by `google_rating` in descending order.
  - Returns the top 5 results.
```

### `verificar_disponibilidade_duo` (verify_duo_availability)
```
Inputs: restaurant_name (str), weekday (str), meal (str), user_time (str, optional)
        weekday: "Segunda-feira" | "Terça-feira" | ... | "Domingo"
        meal:    "almoco" | "jantar"
        user_time: E.g., "20:30"
Output: { available: bool, validation_time: str | null, message: str }

Logic:
  - Finds the restaurant using exact or approximate string matching (fuzzy matching).
  - Accesses the schedule: `restaurant["schedule"][weekday][meal]`.
  - If the value is null/None: returns `{ available: False, ... }`.
  - If the value is a string with a time range (e.g., "18:00 - 23:30"):
    - If `user_time` is provided (e.g., "20:30"), parses both times to `datetime.time` objects and validates if `user_time` is in the interval.
    - Handles day transitions (e.g., up to 01:30 AM).
    - Returns True or False depending on the interval validation.
```

### `obter_detalhes_restaurante` (get_restaurant_details)
```
Inputs: restaurant_name (str)
Output: complete object with:
        { name, cuisine, neighborhood, address, description,
          google_rating, google_reviews_count, google_price_level,
          google_maps_url, phone, website }
```

### `listar_cozinhas_disponiveis` (list_available_cuisines)
```
Inputs: none
Output: list of strings with all unique cuisine types in the JSON database

Use case: allows the agent to suggest valid options when the user
          makes a generic request ("I want to eat well") or types a non-existent cuisine.
```

---

## Phase 2 — System Prompt (prompts.py)

```
You are "Duo Concierge", an expert assistant in gastronomy
and the Duo Gourmet program in the city of Belo Horizonte.

## About Duo Gourmet
The benefit consists of: "order a main dish and get another one of
equal or lesser value free". The benefit is only valid on the days and times
indicated in each restaurant's schedule.

## Your Goal
Help the user choose the best restaurant to use Duo
Gourmet based on their preferences.

## Behavior Rules
1. Always ask for the day and period (lunch or dinner) if not informed.
2. Validate the benefit availability BEFORE recommending.
3. If no restaurant is found with the exact criteria, suggest
   close alternatives (neighboring neighborhood or similar cuisine).
4. When recommending, explain why: cuisine, rating, description, and time.
5. Always include the Google Maps link in the final response.
6. Use the system's current time to infer the day of the week if necessary.
7. Always respond in Brazilian Portuguese.
```

---

## Phase 3 — Agent Loop (agent_core.py)

Implementation with the official `google-genai` library using function calling. The ReAct loop processes calls returned by the model sequentially until the model decides to respond with final text.

```python
import json
from google import genai
from google.genai import types
from agent.tools import (
    buscar_restaurantes,
    verificar_disponibilidade_duo,
    obter_detalhes_restaurante,
    listar_cozinhas_disponiveis
)
from agent.prompts import system_prompt_text

class DuoConciergeAgent:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        # Local mapping for dynamic tool execution
        self.tools_map = {
            "buscar_restaurantes": buscar_restaurantes,
            "verificar_disponibilidade_duo": verificar_disponibilidade_duo,
            "obter_detalhes_restaurante": obter_detalhes_restaurante,
            "listar_cozinhas_disponiveis": listar_cozinhas_disponiveis
        }
        self.tools_list = list(self.tools_map.values())

    def run(self, user_input: str, time_context: str, lat_usuario: float = None, lon_usuario: float = None, history: list = None) -> tuple[str, list[dict], list]:
        """
        Executes the ReAct loop sending the tools and returning the final response,
        the detailed log of intermediate steps executed, and the updated history.
        """
        # ... (Refer to agent_core.py for full implementation details)
```

---

## Phase 4 — Web Interface with Streamlit

### Visual Alignment with DuoList (Design System)

To ensure the assistant's interface is consistent with the visual identity of **DuoList** (composed of a premium dark theme and gold accents), we implement the following customizations:

1. **Streamlit Theme Configuration (`.streamlit/config.toml`)**:
   ```toml
   [theme]
   primaryColor = "#fbcd4b"          # Duo Gourmet Gold (DuoList --accent)
   backgroundColor = "#0f172a"       # Slate Dark (DuoList --bg-color)
   secondaryBackgroundColor = "#1e293b" # Panels/Sidebar (DuoList --panel-bg)
   textColor = "#f8fafc"             # Main Light Text (DuoList --text-main)
   font = "sans serif"
   ```

2. **Font and Branding Injection**:
   We inject the **Outfit** font and custom styles to align the typography with DuoList.

---

## Phase 5 — Real-Time Geolocation (Leaflet)

To allow the agent to calculate precise distances based on the user's current location directly from the browser, we implemented a custom geolocation component in Streamlit using Leaflet and the HTML5 Geolocation API:

1. **Obtaining GPS**: The HTML script inside the custom component's iframe uses `navigator.geolocation.getCurrentPosition` to capture the user's position.
2. **Adjustment Map**: Leaflet renders a Dark Matter theme map with an interactive, draggable gold marker, allowing clicking anywhere on the map to update the location.
3. **JS → Python Communication**: Coordinates are passed reactively back to Streamlit using the Streamlit component messaging protocol (`window.parent.postMessage` with `streamlit:setComponentValue`), eliminating URL reloads.
4. **Database & Parameters Fix**: Adjusted the Haversine calculation to use the correct coordinate keys (`lat` and `lon`) and updated the agent call to receive explicit float values for coordinates.

---

## Future Enhancements (v3)

- **Visit History**: Users can save visited restaurants to avoid repetition.
- **Surprise Mode**: Agent randomly picks a highly-rated restaurant without filters.
- **WhatsApp Bot**: Integration via Twilio or Evolution API for WhatsApp usage.
- **Persistent Multi-turn**: Saving chat history between sessions with a database.

---

## Implementation Checklist

**Backend (Agent)**
- [x] Create the `agent/` directory
- [x] Implement `tools.py` with the 4 core functions
- [x] Write JSON schemas of the tools for Gemini
- [x] Define `prompts.py` with the system prompt
- [x] Implement `utils.py` (current weekday, time formatting)
- [x] Implement main ReAct loop in `agent_core.py`
- [x] Test with at least 5 different scenarios
- [x] Handle edge cases: restaurant not found, outside schedule hours, day without benefit

**Web Interface (Streamlit)**
- [x] Create `agent/app.py` based on the FEAR App pattern
- [x] Implement sidebar with API Key field, Duo description, and Reset button
- [x] Implement message rendering loop with avatares
- [x] Implement expanders to show intermediate tool calls
- [x] Add loading spinner during agent execution
- [x] Add link to the DuoList map in the sidebar
- [x] Test the full conversational flow in the UI

**Real-Time Geolocation (Phase 5)**
- [x] Create HTML/JS script (`gps_component/index.html`) and Python wrapper (`location_picker.py`) integrated with Leaflet
- [x] Implement bi-directional component communication to return `lat`/`lon` without page reloads
- [x] Render interactive map in the sidebar under selected option
- [x] Fix coordinate keys in JSON database backend (`lat` and `lon`)
- [x] Update agent prompts and signatures to receive and prioritize structured GPS coordinates
- [x] Validate distance calculations and sorting in KM in final recommendations
- [x] Add UI toast notifications suggesting GPS activation and confirming lock
- [x] Sync geolocation marker aesthetics with premium pins (gold teardrop + FontAwesome)
- [x] Update Streamlit page icon (favicon) to match DuoList
