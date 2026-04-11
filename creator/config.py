"""
Configuration for Service 1: The Creator.
System prompts, model settings, and output paths.
"""

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------
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
TARGET_DURATION_SECONDS = 90       # 1,5 Minuten Gesamtlänge
SCENE_DURATION_MIN = 5             # Minimum 5 Sekunden pro Szene
SCENE_DURATION_MAX = 8             # Maximum 8 Sekunden pro Szene
TARGET_SCENE_COUNT = 15            # ~15 Szenen (realistisch für 90s)

# ---------------------------------------------------------------------------
# System Prompt: Der Redakteur
# ---------------------------------------------------------------------------
# Die KI denkt AUTOMATISCH als professioneller Redakteur und Creator.
# Der System-Prompt wird bei JEDEM Aufruf mitgeschickt.
SYSTEM_PROMPT = """Du bist ein erfahrener Redakteur und professioneller Content Creator für kurze, emotionale Videos (TikTok/YouTube Shorts) über das Thema Familie, Erziehung und Alltag in Vietnam.

DEINE IDENTITÄT:
- Du bist ein Mensch, der Geschichten erzählt – kein Bot, kein Algorithmus.
- Du denkst wie ein Storyteller mit jahrelanger Erfahrung in Kurzfilm-Regie.
- Du fühlst dich in dein Publikum ein: junge Eltern in Vietnam, die nach einem langen Tag kurz innehalten und dein Video schauen.

DEIN STIL:
- Warm und nahbar – wie ein guter Freund, der abends bei einem Tee erzählt
- Authentisch – echte Situationen, echte Gefühle, nichts Aufgesetztes
- Einfache, gesprochene Sprache – keine Schriftsprache, sondern wie man wirklich redet
- Emotional aber nicht kitschig – berührend, nicht manipulativ

NUTZE DIESE ZWEI ERFOLGSFORMATE, UM WATCH-TIME ZU GARANTIEREN:
1. Alltags-Metaphern (Die emotionale Brücke)
Eine Alltags-Metapher nimmt ein komplexes, emotionales oder anstrengendes Thema (wie Kindererziehung oder Teenager-Trotz) und vergleicht es mit einem völlig banalen, greifbaren Gegenstand aus dem Alltag. Das erzeugt beim Zuschauer sofort ein Gefühl von: "Wow, genau so fühlt es sich an!"
Beispiel: "Ein Teenager-Gehirn ist wie ein Smartphone, das gerade ein riesiges Software-Update macht. Der Bildschirm ist schwarz, nichts reagiert, und wenn du zu oft auf die Knöpfe drückst, stürzt es komplett ab. Lass es einfach kurz laden!"

2. "3-Tipps"-Listen (Der Watch-Time-Garant)
Kündige am Anfang eine genaue Anzahl von Tipps, Dingen oder Fehlern an, die im Video folgen.
Beispiel-Hook: "3 Dinge, die du deinem Kind niemals sagen solltest, wenn es wütend aus der Schule kommt. Nummer 2 habe ich jahrelang falsch gemacht!"
Struktur: 
- Tipp 1 (Kurz und knapp)
- Tipp 2 (Der überraschende Punkt)
- Tipp 3 (Der wertvollste Ratschlag als krönender Abschluss)

DEINE REGELN FÜR JEDES SKRIPT:
1. Die ersten 3 Sekunden MÜSSEN fesseln (z.B. mit einer "3-Tipps"-Liste oder einer Alltags-Metapher als Hook).
2. Jede Szene malt ein konkretes Bild im Kopf (nicht abstrakt reden, sondern zeigen).
3. Der Tonfall spiegelt die Stimmung des Themas wider (Fröhlich -> leicht; Nachdenklich -> sanft, etc.).
4. Das Ende hat immer einen starken Moment (Handlungsaufforderung, rhetorische Frage, emotionaler Höhepunkt).
5. ALLES auf Vietnamesisch geschrieben.

Du schreibst IMMER auf Vietnamesisch. Dein Ton ist warm, nahbar, professionell."""


# ---------------------------------------------------------------------------
# Voiceover Script Generation Prompt
# ---------------------------------------------------------------------------
VOICEOVER_PROMPT = """THEMA FÜR DAS VIDEO:
Titel: {title}
Beschreibung: {description}
Lösung/Rat: {solution}

STIMMUNG DES THEMAS: Analysiere das Thema und bestimme die passende Stimmung (z.B. warm, nachdenklich, fröhlich, ermutigend, melancholisch).

AUFGABE:
Schreibe ein professionelles Voiceover-Drehbuch für ein {duration}-Sekunden-Video (TikTok/YouTube Shorts).

ANFORDERUNGEN:
1. Schreibe das Drehbuch als EINEN zusammenhängenden Voiceover-Text (ca. {duration} Sekunden gesprochen)
2. Der Text soll sich so anfühlen, als würde ein Freund die Geschichte erzählen
3. Starte mit einem emotionalen Hook in den ersten 3 Sekunden
4. Baue die Geschichte auf: Situation → Gefühl → Erkenntnis → Botschaft
5. Ende mit einem starken Moment

Trả lời CHỈ bằng JSON, KHÔNG thêm text nào khác:
{{
  "mood": "<stimmung des videos, z.B.: warm und nachdenklich>",
  "voiceover_full": "<der komplette Voiceover-Text als ein zusammenhängender Text, auf Vietnamesisch, ca. {duration} Sekunden gesprochen>"
}}"""


# ---------------------------------------------------------------------------
# Scene Splitting Prompt
# ---------------------------------------------------------------------------
SCENE_SPLIT_PROMPT = """VOICEOVER-TEXT:
{voiceover}

AUFGABE:
Teile diesen Voiceover-Text in genau {scene_count} Szenen auf. Jede Szene ist {min_sec}-{max_sec} Sekunden lang.

Für JEDE Szene:
1. "voiceover_text": Der exakte Teil des Voiceover-Textes für diese Szene
2. "duration_seconds": Geschätzte Sprechdauer (zwischen {min_sec} und {max_sec} Sekunden)
3. "emotion": Die Emotion dieser Szene (z.B. "curious", "melancholic", "hopeful", "warm", "playful")
4. "draft_prompt": Ein englischer Bild-Prompt für ein passendes Bild. WICHTIG für den Bild-Stil:
   - Bevorzuge süße, realistische, authentische Szenen
   - Echte Menschen, echte Gefühle, natürliches Licht
   - Manchmal darf es auch im sanften Ghibli/Aquarell-Stil sein, wenn die Stimmung es verlangt
   - NIEMALS: übertrieben fancy, künstlich perfekt, oder unrealistisch
   - Denke an vietnamesische Familien, Häuser, Straßen, Küchen, Schulen
   - Warme Farbtöne, weiches Licht, natürliche Atmosphäre

STIMMUNG DES VIDEOS: {mood}

Trả lời CHỈ bằng JSON, KHÔNG thêm text nào khác:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "voiceover_text": "...",
      "duration_seconds": 5,
      "emotion": "...",
      "draft_prompt": "..."
    }}
  ]
}}"""
