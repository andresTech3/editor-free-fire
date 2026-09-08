"""
asset_catalog.py - Complete & Enriched Catalog of Assets for Free Fire Dynamic Video Editor
All assets organized recursively from 'assets/Recurso video Freefire' and subfolders.

Categories Covered:
1. DIAMONDS & MONEY: Diamantes.PNG, green-screen LLUVIA DE DINERO, emotes.MP4
2. PASSES & TOURNAMENTS: torneo.jpeg, gran maestro.png, LLUVIA DE DINERO
3. TOP GLOBALES & RANKING: top global.jpeg, ranking_board.png, regional_top.png
4. SENSITIVITY: sencibilidad.jpg, ECUACIONES PENSANDO green screen, click SFX
5. DPI & MOBILE DEVICES: Asesoria.PNG, ECUACIONES PENSANDO green screen
6. BOOK & WEB GUIDES: codigoheadshot.png, logo.jpeg, LIBRO SECRETO CON IMAGENES
7. EMOTES & CELEBRATIONS: emotes.MP4, MEME TOXIC, AMONG US BAILE, FERNANFLO BAILE
8. WEAPONS & SKINS: AK47 Dragón evolutiva, Groza Booyah, M16 rifle
9. MATCH RESULTS & STATS: resultados.PNG, damage stats
10. CHARACTERS & PROFILE: personaje.png, avatar.png, logo garena.png, likes.PNG
11. MEMES 16:9: 76 full-screen contextual reaction clips in 'PACK DE MEMES'
12. GREEN SCREEN MEMES: 200+ green-screen meme overlays in 'PACK MEMES PANTALLA VERDE'
"""

import os
import re
import unicodedata
from typing import Dict, List, Any, Optional
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_ROOT = os.path.join(PROJECT_ROOT, "assets", "Recurso video Freefire")

# Base directories
DIR_GAMEPLAYS = os.path.join(ASSETS_ROOT, "free fire jugadas")
DIR_IMAGES = os.path.join(ASSETS_ROOT, "Imagenes")
DIR_WEAPONS = os.path.join(DIR_IMAGES, "armas")
DIR_SFX = os.path.join(ASSETS_ROOT, "efectos de sonidos")
DIR_MUSIC = os.path.join(ASSETS_ROOT, "musica")
DIR_PACK_MEMES = os.path.join(ASSETS_ROOT, "PACK DE MEMES")
DIR_GREEN_MEMES = os.path.join(
    ASSETS_ROOT, 
    "PACK MEMES PANTALLA VERDE 1 (manuDT)", 
    "PACK MEMES PANTALLA VERDE 1 (manuDT)"
)
# Fallback to single level if nested doesn't exist
if not os.path.exists(DIR_GREEN_MEMES):
    DIR_GREEN_MEMES = os.path.join(ASSETS_ROOT, "PACK MEMES PANTALLA VERDE 1 (manuDT)")

def normalize_text(text: str) -> str:
    """Normalizes text by removing accents, lowercasing, and stripping punctuation."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())

def find_file_in_dir(directory: str, filename: str) -> Optional[str]:
    """Finds a file in directory handling encoding, case-insensitivity, and accents."""
    if not os.path.exists(directory):
        return None
    full_p = os.path.join(directory, filename)
    if os.path.exists(full_p):
        return full_p
    target = normalize_text(filename)
    try:
        for f in os.listdir(directory):
            if normalize_text(f) == target:
                return os.path.join(directory, f)
    except Exception:
        pass
    return None

# 1. DIAMONDS & MONEY (Diamantes, Recargas, Dinero, Monedas)
DIAMONDS_CATALOG = {
    "chest_image": os.path.join(DIR_IMAGES, "Diamantes.PNG"),
    "pass_poster": os.path.join(DIR_IMAGES, "torneo.jpeg"),
    "green_screen_money": os.path.join(DIR_GREEN_MEMES, "LLUVIA DE DINERO 1.MP4"),
    "emotes_video": os.path.join(DIR_GAMEPLAYS, "emotes.MP4"),
    "sfx": os.path.join(DIR_SFX, "ding-sound-effect_2.mp3"),
    "keywords": [
        "diamante", "diamantes", "recarga", "recargar", "dinero", "plata",
        "oro", "monedas", "comprar diamantes", "diamantes gratis", "millonario",
        "tienda misteriosa", "ruleta magica", "ruleta mágica", "economía", "gastar"
    ]
}

# 2. ELITE PASS & TOURNAMENTS (Pase Élite, Booyah Pass, Torneo)
PASS_AND_TOURNAMENT_CATALOG = {
    "tournament_poster": os.path.join(DIR_IMAGES, "torneo.jpeg"),
    "elite_badge": os.path.join(DIR_IMAGES, "gran maestro.png"),
    "chest_image": os.path.join(DIR_IMAGES, "Diamantes.PNG"),
    "green_screen_money": os.path.join(DIR_GREEN_MEMES, "LLUVIA DE DINERO 1.MP4"),
    "sfx": os.path.join(DIR_SFX, "ding-sound-effect_2.mp3"),
    "keywords": [
        "pase elite", "pase élite", "pases elite", "pases élite", "pase de batalla",
        "el pase", "los pases", "un pase", "comprar pase", "booyah pass",
        "torneo", "torneos", "competencia", "sala", "salas", "campeonato",
        "copa", "premio", "premios"
    ]
}

# 3. TOP GLOBALES & RANKING (Top Global, Ranking, Gran Maestro, Heroico)
TOP_GLOBAL_CATALOG = {
    "leaderboard_image": os.path.join(DIR_IMAGES, "top global.jpeg"),
    "gran_maestro_badge": os.path.join(DIR_IMAGES, "gran maestro.png"),
    "ranking_board": os.path.join(PROJECT_ROOT, "assets", "video free fire", "ranking_board.png"),
    "regional_top": os.path.join(PROJECT_ROOT, "assets", "video free fire", "regional_top.png"),
    "sfx": os.path.join(DIR_SFX, "dun-dun-dun-sound-effect-brass_8nFBccR.mp3"),
    "keywords": [
        "top global", "top globales", "ranking", "gran maestro", "heroico",
        "tabla", "tablas", "puntos", "competitivo", "posicion", "clasificacion",
        "lider", "líder", "mejores del mundo", "regional", "subir de rango", "rango"
    ]
}

# 4. SENSITIVITY & CONFIGURATION (Sensibilidad, Miras, Botón de disparo)
SENSITIVITY_CATALOG = {
    "in_game_menu": os.path.join(DIR_IMAGES, "sencibilidad.jpg"),
    "phone_dpi_menu": os.path.join(DIR_IMAGES, "Asesoria.PNG"),
    "green_screen_thinking": os.path.join(DIR_GREEN_MEMES, "ECUACIONES PENSANDO.mp4"),
    "sfx": os.path.join(DIR_SFX, "mouse-click-sound.mp3"),
    "keywords": [
        "sensibilidad", "sencibilidad", "general", "mira", "punto rojo",
        "mira 2x", "mira 4x", "ajuste", "ajustes", "velocidad", "boton de disparo",
        "botón de disparo", "levantar mira", "afinas", "punto exacto", "control",
        "subes de 10", "subes", "bajas", "configuracion", "configuración"
    ]
}

# 5. DPI & MOBILE DEVICE (Celular, Pantalla, Gama, DPI)
DPI_AND_DEVICE_CATALOG = {
    "device_advice": os.path.join(DIR_IMAGES, "Asesoria.PNG"),
    "sensitivity_img": os.path.join(DIR_IMAGES, "sencibilidad.jpg"),
    "green_screen_thinking": os.path.join(DIR_GREEN_MEMES, "ECUACIONES PENSANDO.mp4"),
    "sfx": os.path.join(DIR_SFX, "mouse-click-sound.mp3"),
    "keywords": [
        "dpi", "celular", "pantalla", "pantallas", "gama", "modelo", "samsung",
        "iphone", "xiaomi", "motorola", "ancho minimo", "ancho mínimo", "tactil", "táctil"
    ]
}

# 6. BOOK, WEBSITE & CODE GUIDES (Código Headshot, Guía, Libro, Web)
BOOK_AND_WEB_CATALOG = {
    "web_banner": os.path.join(DIR_IMAGES, "codigoheadshot.png"),
    "rank_badge": os.path.join(DIR_IMAGES, "gran maestro.png"),
    "logo": os.path.join(DIR_IMAGES, "logo.jpeg"),
    "green_screen_book": os.path.join(DIR_GREEN_MEMES, "LIBRO SECRETO CON IMAGENES.avi"),
    "sfx": os.path.join(DIR_SFX, "ding-sound-effect_2.mp3"),
    "keywords": [
        "libro", "guia", "guía", "pagina", "página", "web", "descarga",
        "descargar", "link", "enlace", "pdf", "sitio", "metodo", "método",
        "secreto", "truco", "paso a paso", "codigo", "código", "valores exactos"
    ]
}

# 7. EMOTES & CELEBRATIONS (Bailes, Emotes, Festejo, Tóxico)
EMOTES_CATALOG = {
    "emotes_video": os.path.join(DIR_GAMEPLAYS, "emotes.MP4"),
    "green_screen_toxic": os.path.join(DIR_GREEN_MEMES, "MEME TOXIC.mp4"),
    "green_screen_amongus": os.path.join(DIR_GREEN_MEMES, "AMONG US BAILE.mp4"),
    "green_screen_fernan": os.path.join(DIR_GREEN_MEMES, "FERNANFLO BAILE.mp4"),
    "green_screen_money": os.path.join(DIR_GREEN_MEMES, "LLUVIA DE DINERO 1.MP4"),
    "sfx": os.path.join(DIR_SFX, "romanceeeeeeeeeeeeee.mp3"),
    "keywords": [
        "emote", "emotes", "baile", "bailar", "toxico", "tóxico", "risa",
        "burlarse", "burla", "celebrar", "festejo", "bailecito", "presumir", "festejar"
    ]
}

# 8. WEAPONS & SKINS (AK47 Dragon, Groza, M16, Modos PVP / Battle Royale)
WEAPONS_CATALOG = {
    "ak47_dragon": os.path.join(DIR_WEAPONS, "9a6f1f7dee653723abd0ee9dada3b5c5-removebg-preview.png"),
    "groza_booyah": os.path.join(DIR_WEAPONS, "b506a7f0c9e7b2fc6dcbb2180f161bbd-removebg-preview.png"),
    "m16_rifle": os.path.join(DIR_WEAPONS, "c79e600e6a5c6f2fecdaac0ee8ced008-removebg-preview.png"),
    "sfx": os.path.join(DIR_SFX, "punch-gaming-sound-effect-hd_RzlG1GE.mp3"),
    "keywords": [
        "arma", "armas", "ak47", "dragon", "flama azul", "evolutiva", "groza",
        "escopeta", "m1014", "mp40", "desert", "rifle", "disparo", "daño",
        "pwp", "pvp", "batel rolal", "battle royale", "duelo de escuadras", "balas"
    ]
}

# 9. MATCH RESULTS & STATS (Resultados, Estadísticas, Daño Efectivo)
RESULTS_AND_STATS_CATALOG = {
    "results_image": os.path.join(DIR_IMAGES, "resultados.PNG"),
    "sfx": os.path.join(DIR_SFX, "ding-sound-effect_2.mp3"),
    "keywords": [
        "resultado", "resultados", "daño efectivo", "daño por segundo",
        "estadistica", "estadisticas", "estadísticas", "kills", "bajas", "partida"
    ]
}

# 10. CHARACTERS & PROFILE (Personaje, Avatar, Garena, Likes)
CHARACTERS_AND_PROFILE_CATALOG = {
    "personaje": os.path.join(DIR_IMAGES, "personaje.png"),
    "avatar": os.path.join(DIR_IMAGES, "avatar.png"),
    "logo_garena": os.path.join(DIR_IMAGES, "logo garena.png"),
    "likes": os.path.join(DIR_IMAGES, "likes.PNG"),
    "keywords": [
        "personaje", "skin", "avatar", "garena", "jugador", "perfil", "cuenta",
        "pro player", "comunidad", "creador"
    ]
}
CHARACTERS_CATALOG = CHARACTERS_AND_PROFILE_CATALOG

# 11. CALL TO ACTION (Likes, Suscríbete, Campanita)
CALL_TO_ACTION_CATALOG = {
    "likes_badge": os.path.join(DIR_IMAGES, "likes.PNG"),
    "green_screen_subscribe": os.path.join(DIR_GREEN_MEMES, "ANIMACIÓN DE LIKE Y SUSCRIBETE 1.mp4"),
    "keywords": [
        "suscribete", "suscríbete", "canal", "like", "campana", "campanita",
        "comenta", "comparte", "apoya", "seguidores"
    ]
}

# 12. SOUND EFFECTS (SFX)
SFX_CATALOG = {
    "ding": os.path.join(DIR_SFX, "ding-sound-effect_2.mp3"),
    "click": os.path.join(DIR_SFX, "mouse-click-sound.mp3"),
    "vine_boom": os.path.join(DIR_SFX, "vine-boom.mp3"),
    "punch": os.path.join(DIR_SFX, "punch-gaming-sound-effect-hd_RzlG1GE.mp3"),
    "error": os.path.join(DIR_SFX, "error_CDOxCYm.mp3"),
    "dramatic": os.path.join(DIR_SFX, "dun-dun-dun-sound-effect-brass_8nFBccR.mp3"),
    "bone_crack": os.path.join(DIR_SFX, "bone-crack.mp3"),
    "censor_beep": os.path.join(DIR_SFX, "censor-beep-1.mp3"),
    "romance": os.path.join(DIR_SFX, "romanceeeeeeeeeeeeee.mp3"),
}

# 13. MUSIC TRACKS
MUSIC_CATALOG = [
    os.path.join(DIR_MUSIC, "Brazilian Phonk Sport by Infraction, Emerel Gray [No Copyright Music]  Hurt.mp3"),
    os.path.join(DIR_MUSIC, "NUNCA MUDA [ ULTRA SLOWED ] [BRAZILIAN PHONK].mp3"),
]

# 14. GAMEPLAY VIDEOS (33 raw recordings in 'free fire jugadas')
def get_gameplay_videos() -> List[str]:
    valid_exts = (".mp4", ".mov", ".m4v")
    if not os.path.exists(DIR_GAMEPLAYS):
        return []
    files = []
    for f in sorted(os.listdir(DIR_GAMEPLAYS)):
        if f.lower().endswith(valid_exts) and "emotes" not in f.lower():
            p = os.path.join(DIR_GAMEPLAYS, f)
            if os.path.isfile(p):
                files.append(p)
    return files

# 15. CONTEXTUAL GREEN SCREEN MEMES (200+ clips in subfolders)
GREEN_SCREEN_MEMES_BY_CONTEXT = {
    "money": {
        "files": ["LLUVIA DE DINERO 1.MP4"],
        "keywords": ["diamantes", "diamante", "dinero", "plata", "oro", "recarga", "pase", "pase elite", "millonario", "comprar", "rico"]
    },
    "top_global": {
        "files": ["GTA MISSION PASSED + RESPECT.mp4", "CONFETI DE CELEBRACIÓN.mp4"],
        "keywords": ["top global", "top globales", "ranking", "gran maestro", "heroico", "tabla", "lider"]
    },
    "subscribe": {
        "files": [
            "ANIMACIÓN DE LIKE Y SUSCRIBETE 1.mp4",
            "ANIMACIÓN DE LIKE Y SUSCRIBETE 2.mp4",
            "ANIMACIÓN DE LIKE Y SUSCRIBETE 3.mp4",
            "ANIMACIÓN DE LIKE Y SUSCRIBETE 4.mp4",
            "ANIMACIÓN SUCRIBETE.mp4",
            "SUSCRIBETE Y ACTIVAR LA CAMPANITA  MOVIL.mp4"
        ],
        "keywords": ["suscribete", "suscríbete", "canal", "like", "campana", "campanita", "comenta", "codigo", "código", "apoya", "comparte"]
    },
    "shock": {
        "files": [
            "PERO QUE A PASAO AURONPLAY.mp4",
            "REACCION DE SORPRENDIDO.mp4",
            "BOB SPONJA GRITANDO.mp4",
            "HOMBRE ASOMBRADO.mp4",
            "WOAW Y GUIÑA EL OJO.mp4"
        ],
        "keywords": ["increible", "increíble", "impresionante", "locura", "no lo vas a creer", "mira esto", "brutal"]
    },
    "god_mode": {
        "files": [
            "SE CONVIERTE EN SUPER SAIYAJIN.mp4",
            "GOKU ULTRA INSTINSTO INCOMPLETO.mp4",
            "MLG GREEN SCREEN.mp4",
            "YO SOY INEBITABLE THANOS.mp4",
            "FUEGO INTENSO.mp4"
        ],
        "keywords": ["insano", "modo diablo", "nivel dios", "ultra instinto", "nadie te para", "imbatible", "todo rojo", "rojos", "headshot"]
    },
    "fail": {
        "files": [
            "TOMAAAA DON RAMON.mp4",
            "GTA5 WASTED  (ELIMINADO).mp4",
            "-HAS MUERTO- MINECRAFT.mp4",
            "MEME DEL ATAUD (ASTRONOMIA) MINECRAFT.mp4",
            "ERROR EXTREMO WINDOWS.mp4"
        ],
        "keywords": ["fallar", "manco", "morir", "te matan", "lobby", "perder", "wasted", "fallé", "no sirves", "muerto", "mancos", "no hay", "mentira", "falso", "magica", "mágica"]
    },
    "thinking": {
        "files": [
            "LA ROCA SERIO MEME.mp4",
            "PERO QUE A PASAO AURONPLAY.mp4",
            "BOB SPONJA GRITANDO.mp4",
            "TOMAAAA DON RAMON.mp4"
        ],
        "keywords": ["estrategia", "pensar", "calcular", "analizar", "secreto", "truco", "formula", "fórmula", "mente", "cerebro", "valor", "subes", "afinas", "punto exacto", "control", "proceso", "pantalla", "responde"]
    },
    "laugh": {
        "files": [
            "HEHE BOI.mp4",
            "CARA TROLL.mp4",
            "HEHEHEHA CLASH ROYALE.mp4",
            "JONAH JAMESON RIENDOSE.mp4",
            "NEGRO RIENDOSE.mp4"
        ],
        "keywords": ["risa", "jaja", "chiste", "humillar", "burlarse", "troll"]
    },
    "dance": {
        "files": [
            "AMONG US BAILE.mp4",
            "FERNANFLO BAILE.mp4",
            "CALAMARDO BAILANDO BOB SPONJA.mp4",
            "BAILE FORNITE.mp4"
        ],
        "keywords": ["baile", "bailar", "celebrar", "festejo", "bailecito"]
    },
    "shooting": {
        "files": [
            "DISPAROS EN LA PANTALLA.mp4",
            "DISPARO CON SANGRE.mp4"
        ],
        "keywords": ["disparo", "disparos", "balas", "tiro", "sangre"]
    }
}

def get_green_meme_path(filename: str) -> Optional[str]:
    """Resolves green screen meme path with encoding & normalization tolerance."""
    return find_file_in_dir(DIR_GREEN_MEMES, filename)

def get_pack_memes_list() -> List[str]:
    """Returns all 16:9 full-screen memes from PACK DE MEMES."""
    if not os.path.exists(DIR_PACK_MEMES):
        return []
    return [
        os.path.join(DIR_PACK_MEMES, f)
        for f in sorted(os.listdir(DIR_PACK_MEMES))
        if f.endswith(".mp4") and not f.startswith(".")
    ]
