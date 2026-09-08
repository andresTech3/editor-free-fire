"""
Enhance pack_de_memes_transcripts.json with categories, keywords, and sentiment tags.
"""

import json
import os

catalog_path = r"core/pack_de_memes_transcripts.json"
with open(catalog_path, "r", encoding="utf-8") as f:
    items = json.load(f)

for item in items:
    fname = item["filename"].lower()
    speech = item.get("speech", "").lower()
    tags = []
    category = "general"

    # Specific recognized memes
    if "auronplay" in fname:
        category = "dance"
        tags = ["auronplay", "baile", "bailar", "fiesta", "musica", "celebracion"]
    elif "emotiza" in speech or "motisa" in speech or "chamarc" in speech or "chamaco" in speech:
        category = "emotes"
        tags = ["emotes", "emotiza", "insana", "insano", "baile", "chamaco", "emboscada"]
    elif "esto es cine" in speech or "cinergrafo" in speech or "sinergrafo" in speech:
        category = "god_mode"
        tags = ["cine", "esto es cine", "obra de arte", "pro", "epico", "jugada maestra"]
    elif "mira a bobo" in speech or "miras bobo" in speech or "anda pacha" in speech or "anda pa alla" in speech:
        category = "toxic"
        tags = ["que miras bobo", "messi", "humillacion", "toxic", "toxico", "burla", "vencido"]
    elif "la queso" in speech or "soporte" in speech:
        category = "toxic"
        tags = ["la que soporte", "y la queso", "toxic", "orgullo", "burla"]
    elif "no guanto mas" in speech or "no aguanto mas" in speech or "necesito su ayuda" in speech:
        category = "cry"
        tags = ["no aguanto mas", "ayuda", "triste", "llanto", "desesperacion", "perder"]
    elif "ha ha ha" in speech or "hahaha" in speech or "jaja" in speech:
        category = "laugh"
        tags = ["risa", "jaja", "chiste", "burlarse", "humillar"]
    elif "te salvaste de mi maldito" in speech or "berga" in speech:
        category = "rage"
        tags = ["enojo", "rabia", "maldito", "grito", "disparo"]
    elif "esta vivo" in speech or "al fin" in speech:
        category = "victory"
        tags = ["esta vivo", "victoria", "resucito", "celebrar"]
    elif "see you again" in speech:
        category = "fail"
        tags = ["f en el chat", "despedida", "muerte", "see you again", "lobby"]
    elif "cabello" in speech:
        category = "shock"
        tags = ["shock", "locura", "inesperado"]
    elif "what" in speech or "que" in speech:
        category = "wtf"
        tags = ["que paso", "what", "confusion", "no entiendo"]
    else:
        # Categorize by duration or secondary cues
        if item["duration"] < 3.0:
            category = "reaction_quick"
            tags = ["reaccion", "rapido", "impacto"]
        elif item["duration"] > 10.0:
            category = "scene"
            tags = ["escena", "momento"]
        else:
            category = "general"
            tags = ["meme", "clip"]

    item["category"] = category
    item["tags"] = tags

with open(catalog_path, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Updated {len(items)} items in {catalog_path}")
