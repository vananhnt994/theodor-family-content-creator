# 📚 Input Directory Guide

Dieser Ordner dient zur Bereitstellung von Quellmaterialien (Bücher, Artikel) für die Content-Pipeline.

Aus Urheberrechts- und Speicherplatzgründen sind Buch-PDFs im Git-Repository ignoriert.

---

## Ordnerstruktur

```text
input/
├── README.md               # Diese Anleitung
├── artikel.txt             # Lokale Artikel / Notizen für die Shorts-Pipeline
├── shorts/
│   ├── artikel.txt         # Alternative Artikelquelle für Shorts
│   └── books/              # PDF-Bücher für Kurzvideos (Erziehung, Psychologie, etc.)
└── long/
    ├── books/              # PDF-Bücher für Long-Form Gute-Nacht-Geschichten
    └── books_natur/        # Bücher / Geschichten für Natur- und Tierwelten
```

---

## Eigene Bücher hinzufügen

1. **Shorts-Bücher (Erziehungs- & Lebenshilfe-Themen):**
   - Lege deine PDF-Dateien in `input/shorts/books/`.
   - Die Pipeline (`trend_scout/book_reader.py`) liest die Kapitel aus und wählt automatisch unverarbeitete Passagen für Kurzskripte aus.

2. **Long-Form-Bücher (Gute-Nacht-Geschichten):**
   - Lege deine PDF-Dateien in `input/long/books/` (z. B. gemeinfreie Märchen von Grimm, Andersen).
   - Die Pipeline (`run_long_pipeline.py`) verarbeitet diese sequentiell oder im Story-Critic-Modus.

3. **Artikel & Web-Scraping:**
   - In `input/artikel.txt` können Rohtexte abgelegt werden.
   - Alternativ scraped `trend_scout` automatisch die in `channels/channel.example.json` konfigurierten Webquellen.
