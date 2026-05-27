# Duo Concierge 🍽️

This is **Duo Concierge**, an AI agent specialized in the Duo Gourmet program in Belo Horizonte.

Built on top of the **DuoList BH** interactive map, this agent utilizes the Google Gemini API to help you decide where to use your benefit based on simulated context, time, and location.

## 🚀 How to Run the App
1. Clone or download this project
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python -m streamlit run agent/app.py`

## 🔑 Configuration
You will need a **Gemini API Key**. You can obtain one for free at [Google AI Studio](https://aistudio.google.com/). After starting the interface, paste the key in the left sidebar.

## 📁 File Structure
- `restaurantes_bh.json` - The DuoList database.
- `agent/app.py` - Streamlit visual interface.
- `agent/agent_core.py` - Agent initialization logic, prompts, and communication with the Google GenAI SDK.
- `agent/tools.py` - Tools called by the agent (Haversine spatial filtering, schedule checking, database loading).
- `agent/prompts.py` - Base system prompt guiding the model's behavior and persona.
- `agent/utils.py` - Text normalizers and date/time parsers.
