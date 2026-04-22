from core.services.llm import call_ollama
from verbalization.coaching.prompts import (
    build_load_prompt,
    build_progress_prompt,
    build_regularity_prompt,
    build_volume_prompt,
)


def verbalize_coaching_llm(
    user_message: str,
    coaching_type: str,
    signature: dict,
    facts: dict,
    already_started: bool = False,
) -> str:
    base_prompt = f"""
REGLES ABSOLUES :
- Tu peux interpreter, mais tu NE DOIS PAS diagnostiquer
- Tu NE DOIS PAS inventer de chiffres
- Tu NE DOIS PAS promettre de resultats
- Tu NE DOIS PAS proposer de plan d'entrainement
- Reponse courte : 3 a 5 phrases maximum

PROFIL LONG TERME DU COUREUR
{signature}
"""
    if coaching_type == "REGULARITY":
        specific_prompt = build_regularity_prompt(
            message=user_message,
            facts=facts,
            already_started=already_started,
        )
    elif coaching_type == "VOLUME":
        specific_prompt = build_volume_prompt(
            message=user_message,
            facts=facts,
            already_started=already_started,
        )
    elif coaching_type == "LOAD":
        specific_prompt = build_load_prompt(
            message=user_message,
            facts=facts,
            already_started=already_started,
        )
    elif coaching_type == "PROGRESS":
        specific_prompt = build_progress_prompt(
            message=user_message,
            facts=facts,
            already_started=already_started,
        )
    else:
        return "Je ne suis pas sur de ce que tu veux analyser."

    final_prompt = base_prompt + "\n\n" + specific_prompt

    return call_ollama(
        prompt=(
            "Tu es un coach de course a pied humain, calme et experimente. "
            "Tu reponds STRICTEMENT dans la langue du message utilisateur."
            f"\n\n{final_prompt}"
        )
    ).strip()
