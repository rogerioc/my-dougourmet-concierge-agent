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
        # Utilizando o flash, pois é mais rápido e o 2.5 traz melhor reasoning
        self.model = "gemini-2.5-flash"
        
        self.tools_map = {
            "buscar_restaurantes": buscar_restaurantes,
            "verificar_disponibilidade_duo": verificar_disponibilidade_duo,
            "obter_detalhes_restaurante": obter_detalhes_restaurante,
            "listar_cozinhas_disponiveis": listar_cozinhas_disponiveis
        }
        self.tools_list = list(self.tools_map.values())

    def run(self, user_input: str, time_context: str, history: list = None) -> tuple[str, list[dict], list]:
        """
        Executa o loop ReAct chamando o Gemini e processando as function calls
        até devolver a resposta textual final, mantendo o histórico de chat.
        """
        if history is None:
            history = []
            
        history.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"Contexto do Sistema (invisível p/ usuário): {time_context}\n\nEntrada do Usuário: {user_input}")
                ]
            )
        )
        
        intermediate_steps = []
        max_turns = 8
        
        for _ in range(max_turns):
            response = self.client.models.generate_content(
                model=self.model,
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt_text,
                    tools=self.tools_list,
                    temperature=0.4
                )
            )
            
            if response.function_calls:
                # Gemini exige que o histórico de function calls geradas seja adicionado como role 'model'
                history.append(response.candidates[0].content)
                
                tool_responses = []
                for call in response.function_calls:
                    name = call.name
                    args = call.args
                    
                    try:
                        func = self.tools_map[name]
                        args_dict = dict(args) if args else {}
                        result = func(**args_dict)
                    except Exception as e:
                        result = {"error": str(e)}
                    
                    intermediate_steps.append({
                        "tool": name,
                        "args": args_dict,
                        "result": result
                    })
                    
                    # Adiciona a resposta da ferramenta. Google SDK espera um dicionário com chave fixa ou algo serializável.
                    tool_responses.append(
                        types.Part.from_function_response(
                            name=name,
                            response={"result": result}
                        )
                    )
                
                # As respostas das funções entram no histórico como role 'user' no padrão GenAI SDK
                history.append(
                    types.Content(
                        role="user",
                        parts=tool_responses
                    )
                )
                continue
            else:
                # Salva a resposta final do modelo no histórico
                if response.candidates and response.candidates[0].content:
                    history.append(response.candidates[0].content)
                return response.text, intermediate_steps, history
                
        return "Desculpe, precisei interromper a busca pois demorou demais para encontrar algo. Tente ser mais específico!", intermediate_steps, history
                
        return "Desculpe, precisei interromper a busca pois demorou demais para encontrar algo. Tente ser mais específico!", intermediate_steps
