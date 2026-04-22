from core.services.llm import call_ollama


def verbalize_period_summary_llm(
    user_message: str,
    summary,
) -> str:
    system_prompt = (
        "Tu es un narrateur factuel. "
        "Tu fais un bilan complet d'une periode d'entrainement."
    )
    user_prompt = f"""
Question utilisateur :
"{user_message}"

Donnees factuelles :
- periode : {summary.period}
- seances : {summary.sessions}
- distance totale : {round(summary.distance_km, 1)} km
- duree totale : {round(summary.duration_min, 0)} minutes
- frequence cardiaque moyenne : {round(summary.avg_hr, 0) if summary.avg_hr else "non disponible"} bpm
- denivele total : {round(summary.elevation_m, 0)} m
- calories actives : {round(summary.active_kcal, 0)} kcal

Regles STRICTES :
- ne deduis aucune information non fournie
- ne fais pas de comparaison
- ne donnes pas de conseils
- n'invente aucun chiffre
- reponse claire, fluide, 3-4 phrases maximum

Obligations :
- reponds dans la langue de la question
- Si la question est en francais, reponds en francais.

Reponse :
"""
    return call_ollama(prompt=f"{system_prompt}\n\n{user_prompt}").strip()
