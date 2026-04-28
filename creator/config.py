"""
Configuration for Service 1: The Creator.
System prompts, model settings, and output paths.
"""

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from channel_config import load_channel_config

channel_cfg = load_channel_config()

GEMINI_MODEL = "gemini-2.5-flash-lite"

# ---------------------------------------------------------------------------
# Input / Output
# ---------------------------------------------------------------------------
INPUT_DIR = "output"
INPUT_FILENAME = "thema.json"
OUTPUT_DIR = "output"
OUTPUT_FILENAME = "roh_skript.json"

# ---------------------------------------------------------------------------
# Video Constraints
# ---------------------------------------------------------------------------
TARGET_DURATION_SECONDS = 60        # 1 Minute Gesamtlänge
SCENE_DURATION_MIN = 5              # Minimum 5 Sekunden pro Szene
SCENE_DURATION_MAX = 8              # Maximum 8 Sekunden pro Szene
TARGET_SCENE_COUNT = 10             # ~10 Szenen (realistisch für 60s)

# ---------------------------------------------------------------------------
# System Prompt: Der Redakteur
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""Du bist ein direkter, faktischer Drehbuchautor für informative 60-Sekunden-Shorts über {channel_cfg.get('topic', 'den Familienalltag')}.
Deine Aufgabe: Bringe das Thema präzise auf den Punkt. Liefere harte Fakten und klare Aussagen, keine Umschweife. Entscheide basierend auf dem Artikel, ob es wirkungsvoller ist, eine authentische Geschichte aus der Ich-Perspektive zu erfinden, oder als neutraler Erzähler zu berichten.

STRIKTE REGELN:
1. Sprache: Das Voiceover (voiceover_text) MUSS auf {channel_cfg.get('language', 'Vietnamesisch')} geschrieben sein.
2. Länge (HARTES LIMIT): Schreibe maximal 130 bis 140 Wörter. Jeder Text, der länger ist, wird abgelehnt. Dies zwingt das Audio, sicher unter 59 Sekunden zu bleiben.
3. Szenen: Erstelle exakt 4 bis 6 chronologische visuelle Szenen.
4. Stille (Ma): Füge an emotionalen Stellen mindestens zwei Mal das Tag <break time="1.0s" /> in den {channel_cfg.get('language', 'vietnamesischen')} Text ein.
5. Hook: Der allererste Satz MUSS eine provokante Frage oder ein direkter Schmerzpunkt für Eltern sein (z. B. 'Mẹ càng bao bọc, con trai càng vô dụng!'). Keine ruhige Szene am Anfang.
6. Stil: Verwende keine poetischen Beschreibungen wie 'die Uhr tickt' oder 'ein unordentliches Zimmer'. Liefere nur harte Fakten, Ratschläge und klare Aussagen. Am Ende lieferst du genau, was der Wert von dem Inhalt direkt ist.
7. Bild-Prompt: Liefere zu jeder Szene eine simple ENGLISCHE Bildbeschreibung. GIB DEN CHARAKTEREN KEINE NAMEN! Nutze Rollen (z.B. "a mother", "a 5-year-old girl").

Halte dich bei der Formatierung exakt an die im jeweiligen Schritt geforderte JSON-Struktur!
"""


# ---------------------------------------------------------------------------
# Voiceover Script Generation Prompt
# ---------------------------------------------------------------------------
VOICEOVER_PROMPT = f"""THEMA FÜR DAS VIDEO:
Titel: {{title}}
Beschreibung: {{description}}
Lösung/Rat: {{solution}}

AUFGABE:
Schreibe ein professionelles Voiceover-Drehbuch für ein {{duration}}-Sekunden-Video (TikTok/YouTube Shorts).

STRIKTE LÄNGEN-REGEL:
Schreibe maximal 130 bis 140 Wörter. Jeder Text, der länger ist, wird abgelehnt.

STIMMUNG: Analysiere das Thema und bestimme die passende Grundstimmung (z.B. direkt, ernst, informativ).

STORYTELLING-STRUKTUR (in dieser Reihenfolge):
1. HARTER HOOK (erste 5 Sekunden): Der allererste Satz MUSS eine provokante Frage oder ein direkter Schmerzpunkt für Eltern sein (z. B. 'Mẹ càng bao bọc, con trai càng vô dụng!'). Beginne auf keinen Fall mit einer ruhigen Szene.
2. DIE SITUATION (20 Sekunden): Erkläre die Problematik oder Situation aus dem Artikel. Entscheide hierbei dynamisch, ob du die Geschichte aus der Ich-Perspektive eines Betroffenen erzählst oder ob du als neutraler Erzähler berichtest.
3. VORSCHLÄGE & LÖSUNGEN (25 Sekunden): Teile die *konkreten* Ratschläge und Lösungsansätze *exakt aus dem Artikel*. Wenn das Thema eine spezifische logische Aufgabe ist, erkläre sie zwingend.
4. DIREKTER WERT (10 Sekunden): Am Ende lieferst du genau, was der Wert von dem Inhalt direkt ist.

STIL-REGELN (SHOW, DON'T TELL):
- Verwende keine poetischen Beschreibungen wie 'die Uhr tickt' oder 'ein unordentliches Zimmer'.
- Liefere nur harte Fakten, Ratschläge und klare Aussagen.
- KEINE Romantik-Stile oder pure Theorie-Listen.
- Nur fließender, direkter Erzähltext.
- Füge mindestens 2x das Tag <break time="1.0s" /> an wichtigen Stellen ein.

Trả lời CHỈ bằng JSON, KHÔNG thêm text nào khác:
{{{{
  "mood": "<stimmung des videos, z.B.: ernst und informativ>",
  "voiceover_full": "<der komplette Voiceover-Text als ein zusammenhängender Text, auf {channel_cfg.get('language', 'Vietnamesisch')}>",
  "seo": {{{{
    "title": "<Ein klickstarker, neugierig machender Titel auf {channel_cfg.get('language', 'Vietnamesisch')}, max. 60 Zeichen>",
    "description": "<SEO-optimierte Videobeschreibung. Erste zwei Sätze mit den wichtigsten Suchbegriffen>"
  }}}}
}}}}"""


# ---------------------------------------------------------------------------
# Scene Splitting Prompt
# ---------------------------------------------------------------------------
SCENE_SPLIT_PROMPT = f"""VOICEOVER-TEXT:
{{voiceover}}

AUFGABE:
Teile diesen Voiceover-Text in genau {{scene_count}} Szenen auf. Jede Szene ist {{min_sec}}-{{max_sec}} Sekunden lang.

Für JEDE Szene:
1. "voiceover_text": Der exakte Teil des Voiceover-Textes für diese Szene
2. "duration_seconds": Geschätzte Sprechdauer (zwischen {{min_sec}} und {{max_sec}} Sekunden)
3. "emotion": Die Emotion dieser Szene (z.B. "peaceful", "warm", "gentle", "hopeful", "serene")
4. "draft_prompt": Ein englischer Bild-Prompt für ein passendes Bild. WICHTIG für Bild-Stil und Konsistenz:
   - CHARACTER CONSISTENCY: Lege für Charaktere GANZ GENAUE, feste visuelle Eigenschaften fest (Rolle, Alter, Kleidung, Kleiderfarbe, Frisur). GIB DEN CHARAKTEREN KEINE NAMEN (verwende stattdessen "a mother", "a father", "a 5-year-old girl", "a teacher"). Verwende EXAKT DIESELBE detaillierte Beschreibung (z.B. "a 5-year-old Vietnamese girl with short black hair wearing a pink dress") in JEDEM Prompt, in dem diese Person auftaucht! Erwähne auch in Detailaufnahmen IMMER den Charakter und das Outfit (z.B. statt nur "Button" schreibe "The button on the pink dress of a 5-year-old girl...").
   - AVOID MATH & NUMBERS: KI-Bildgeneratoren können nicht zählen oder rechnen. Fordere NIEMALS "17 Kamele" oder "3 Wege" oder "eine Rechenaufgabe" auf einem Bild an. Beschreibe stattdessen simple visuelle Metaphern oder einfache Charakter-Porträts (z.B. "a few camels", "the sons looking amazed", "a single lightbulb").
   - ALL scenes MUST be in flat 2D Studio Ghibli anime style. Do NOT use realistic or photographic styles.
   - BACKGROUNDS must be SIMPLE and MINIMAL: soft pastel colors, gentle gradients, or simple nature elements. NO busy or detailed environments.
   - MOOD: Every scene must radiate calm, peace, and serenity. Warm sunset tones, soft golden light, gentle breeze.
   - Warme Farbtöne, weiches Licht, natürliche Atmosphäre.

STIMMUNG DES VIDEOS: {{mood}}

Trả lời CHỈ bằng JSON, KHÔNG thêm text nào khác:
{{{{
  "scenes": [
    {{{{
      "scene_number": 1,
      "voiceover_text": "...",
      "duration_seconds": 5,
      "emotion": "...",
      "draft_prompt": "..."
    }}}}
  ]
}}}}"""
