from core.services.llm import call_ollama


def verbalize_period_comparison_llm(
    user_message: str,
    left_period: str,
    right_period: str,
    left_value: float | int,
    right_value: float | int,
    delta: float | int | None,
) -> str:
    """
    Verbalise une comparaison deja calculee.
    Les valeurs sont fournies par l'executor et ne doivent pas etre modifiees.
    """
    system_prompt = (
        "Tu es un coach sportif factuel. "
        "Tu compares des donnees sans jamais les modifier."
    )

    user_prompt = f"""
Question utilisateur :
"{user_message}"

Donnees factuelles :
- periode gauche : {left_period}
- valeur gauche : {round(left_value, 2)}
- periode droite : {right_period}
- valeur droite : {round(right_value, 2)}
- delta : {round(delta, 2) if delta is not None else "non disponible"}

Regles :
- tu compares UNIQUEMENT les valeurs fournies
- n'invente aucun chiffre
- reponse fluide, naturelle, 2-3 phrases maximum
- pas de conseils
- tu NE DOIS PAS deduire ou supposer d'autres metriques

Obligations :
- reponds dans la langue de la question
- Si la question est en francais, reponds en francais.

Reponse :
"""
    return call_ollama(prompt=f"{system_prompt}\n\n{user_prompt}").strip()
