# Duo Concierge 🍽️

Este é o **Duo Concierge**, um agente de IA especializado no programa Duo Gourmet em Belo Horizonte.

Criado com base no mapa interativo **DuoList BH**, este agente utiliza a API do Google Gemini para ajudar você a decidir onde usar seu benefício baseado em contexto, horário e localização simulados.

## 🚀 Como iniciar a interface
1. Clone ou baixe este projeto
2. Instale as dependências: `pip install -r requirements.txt`
3. Inicie o aplicativo: `python -m streamlit run agent/app.py`

## 🔑 Configuração
Você precisará de uma **API Key do Gemini**. Você pode obtê-la gratuitamente no [Google AI Studio](https://aistudio.google.com/). Após iniciar a interface, insira a chave na barra lateral esquerda.

## 📁 Estrutura de Arquivos
- `restaurantes_bh.json` - A base de dados do DuoList.
- `agent/app.py` - Interface visual usando Streamlit.
- `agent/agent_core.py` - Lógica de inicialização do agente, prompts e comunicação com a Google GenAI SDK.
- `agent/tools.py` - As ferramentas chamadas pelo agente (Filtro espacial por Haversine, checagem do schedule, leitura do banco).
- `agent/prompts.py` - Prompt base que direciona o comportamento e persona do modelo.
- `agent/utils.py` - Normalizadores de texto e manipuladores de data/hora.
