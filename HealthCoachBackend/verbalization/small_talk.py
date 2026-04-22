from core.services.llm import call_ollama


def verbalize_small_talk_llm(user_message: str) -> str:
    system_prompt = (
        "Tu es un assistant running bienveillant. "
        "Tu reponds de maniere naturelle et humaine."
    )
    user_prompt = f"""
Message utilisateur :
"{user_message}"

Regles :
- pas d'acces aux donnees
- pas de chiffres inventes
- pas d'analyse medicale
- reponse courte (1-2 phrases)
- ton chaleureux et simple
- ne force pas une question metier

Reponse :
"""
    return call_ollama(prompt=f"{system_prompt}\n\n{user_prompt}").strip()
