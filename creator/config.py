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
SYSTEM_PROMPT = f"""Du bist ein vietnamesischer Erziehungsexperte und ein direkter, faktischer Drehbuchautor für informative 60-Sekunden-Shorts über {channel_cfg.get('topic', 'den Familienalltag')}.
Deine Aufgabe: Bringe das Thema präzise auf den Punkt. Liefere harte Fakten und klare Aussagen, keine Umschweife. Der Fokus liegt IMMER auf dem konkreten Mehrwert (Value) für die Eltern – was lernen sie heute? Schreibe AUSSCHLIESSLICH aus der Perspektive der Eltern oder als Berater FÜR die Eltern. Verwende niemals die Ich-Perspektive eines Kindes.

STRIKTE REGELN:
1. Sprache: Das Voiceover (voiceover_text) MUSS auf {channel_cfg.get('language', 'Vietnamesisch')} geschrieben sein.
2. Länge (HARTES LIMIT): Schreibe maximal 130 bis 140 Wörter. Jeder Text, der länger ist, wird abgelehnt. Dies zwingt das Audio, sicher unter 59 Sekunden zu bleiben.
3. Szenen: Erstelle exakt 4 bis 6 chronologische visuelle Szenen.
4. Stille (Ma): Füge an emotionalen Stellen mindestens zwei Mal das Tag <break time="1.0s" /> in den {channel_cfg.get('language', 'vietnamesischen')} Text ein.
5. Hook: Der allererste Satz MUSS eine provokante Frage oder ein direkter Schmerzpunkt für Eltern sein, der EXAKT zum aktuellen Thema passt (z. B. 'Bạn có đang vô tình làm hại con mình?' oder 'Sự thật chấn động về...'). Erfinde jedes Mal einen neuen, packenden Hook. Keine ruhige Szene am Anfang.
6. Stil: Verwende keine poetischen Beschreibungen wie 'die Uhr tickt' oder 'ein unordentliches Zimmer'. Liefere nur harte Fakten, Ratschläge und klare Aussagen. Am Ende lieferst du genau, was der Wert von dem Inhalt direkt ist.
7. Bild-Prompt: Liefere zu jeder Szene eine simple ENGLISCHE Bildbeschreibung. GIB DEN CHARAKTEREN KEINE NAMEN! Nutze Rollen (z.B. "a mother", "a 5-year-old girl").
8. KEINE NAMEN IM VOICEOVER: Verwende niemals Eigennamen für Charaktere im Voiceover-Text (z.B. Giang, Lukas, etc.). Nutze stattdessen allgemeine Bezeichnungen wie "ba mẹ", "người mẹ", "người cha", "con cái", "đứa trẻ"...

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
1. HARTER HOOK (erste 5 Sekunden): Der erste Satz MUSS ein konkretes Problem oder eine Angst der Eltern ansprechen, das direkt aus dem Artikel/Thema hervorgeht (z. B. 'Bạn sẽ làm gì khi phát hiện...' oder 'Tại sao điều này lại quan trọng?'). Beginne auf keinen Fall mit einer ruhigen Szene. Erstelle einen Hook, der die Zuschauer sofort fesselt.
2. DIE SITUATION (15 Sekunden): Erkläre die Problematik oder Situation aus dem Artikel. Warum ist das für Eltern relevant? Schreibe AUSSCHLIESSLICH aus der Perspektive der Eltern.
3. DER MEHRWERT & LÖSUNG (30 Sekunden): Teile die *konkreten* Ratschläge und Lösungsansätze *exakt aus dem Artikel*. Dies ist der wichtigste Teil des Videos. Erkläre den Wert direkt und verständlich. Wenn das Thema eine spezifische Aufgabe ist, erkläre sie zwingend.
4. DIREKTER WERT & CTA (10 Sekunden): Die letzten 5 bis 8 Sekunden des Textes MÜSSEN einen klaren 'Call to Action' enthalten, der auf ein Affiliate-Produkt oder die Kommentare verweist (z. B. 'Tham khảo cuốn sách ở link dưới nha!').

STIL-REGELN (SHOW, DON'T TELL):
- Verwende keine poetischen Beschreibungen wie 'die Uhr tickt' oder 'ein unordentliches Zimmer'.
- Liefere nur harte Fakten, Ratschläge und klare Aussagen.
- KEINE Romantik-Stile oder pure Theorie-Listen.
- Nur fließender, direkter Erzähltext.
- KEINE NAMEN: Verwende niemals Eigennamen für Charaktere. Nutze Rollen wie "cha mẹ", "người mẹ", "con cái"...
- Füge ít nhất 2x das Tag <break time="1.0s" /> an wichtigen Stellen ein.

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
   - CHARACTER CONSISTENCY (MANDATORY): Zwinge das Skript, vor JEDES Bild feste Attribute zu setzen. Du darfst NIEMALS generische Begriffe wie "mother and father" verwenden. Stattdessen MUSS der Code generieren: z.B. "35-year-old Vietnamese mother with short black hair and 40-year-old Vietnamese father with glasses". Verwende EXAKT DIESELBE extrem restriktive und detaillierte Beschreibung in JEDEM Prompt, in dem diese Personen auftauchen! Keine Ausnahmen!
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
