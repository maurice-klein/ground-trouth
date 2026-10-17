# Technische Dokumentation

## Architektur

Das Repository bildet eine dateibasierte, lokal ausgeführte Evaluationsstrecke:

1. `src/ingest/` analysiert PDFs und rendert Seitenbilder mit PyMuPDF.
2. `src/preprocess/` begradigt Bilder und verbessert Kontrast beziehungsweise Binarisierung mit OpenCV, NumPy und Pillow.
3. Label Studio dient außerhalb des Repositories als manuelle Annotationsoberfläche; Exporte werden unter `data/eval/raw/` abgelegt.
4. `scripts/process_label_studio_export.py` wandelt den Export in eine dokumentweise Ground-Truth-Struktur um.
5. Eine separate IDP-Pipeline legt OCR-, Feld- und Tabellenprognosen unter `data/processed/` ab.
6. `src/eval/run_eval.py` vergleicht Ground Truth und Prognosen und schreibt JSON- und HTML-Berichte nach `out/reports/`.

`configs/base.yaml` beschreibt ein größeres Zielbild mit LayoutParser, PaddleOCR, Camelot und einem deutschen BERT-NER-Modell. Der geprüfte Code in diesem Repository implementiert jedoch vor allem PDF-Analyse, Vorverarbeitung, Annotationsexport und Evaluation. Eine vollständige Orchestrierung aller konfigurierten Engines ist nicht belegt.

## Datenmodell und Dateigrenzen

| Bereich | Inhalt | Rolle |
|---|---|---|
| `data/eval/raw/` | Label-Studio-Exporte | rohe manuelle Annotationen |
| `data/eval/<dokument>/` | OCR-Referenz, strukturierte Entitäten, Referenztabelle | Ground Truth |
| `data/processed/<dokument>/` | OCR-, Feld- und Tabellenergebnisse | Pipeline-Prognose |
| `out/reports/<zeitpunkt>/` | `eval_summary.json` und `eval_report.html` | aggregierter Nachweis |

Die Wahrheit über einzelne Felder liegt im jeweiligen Ground-Truth-Dokument. Der Bericht ist eine abgeleitete Sicht und ersetzt weder Annotation noch Pipeline-Ausgabe.

## Schnittstellen

### PDF → Seitenbilder

- **Quelle/Ziel:** lokale PDF-Datei → dokumentbezogener Bildordner
- **Auslöser:** manueller CLI-Aufruf von `src/ingest/pdf2images.py`
- **Mechanismus:** lokaler Dateizugriff, PyMuPDF, PNG
- **Fehlerweg:** ungültige oder nicht lesbare PDFs werden als Fehler sichtbar; ein zentraler Retry ist nicht implementiert
- **Versionierung/Owner:** nicht festgelegt; Owner Maurice soweit durch das Repository belegt

### Seitenbilder → Label Studio → Export

- **Quelle/Ziel:** vorverarbeitete Bilder → externe Label-Studio-Instanz → JSON-Export
- **Fachlicher Zweck:** manuelle Referenzannotation
- **Mechanismus:** Dateien und manueller Export; Authentifizierung und Instanzkonfiguration sind nicht dokumentiert
- **Daten:** potenziell personenbezogene und finanzielle Inhalte
- **Fehlerweg:** fehlende Annotationen werden übersprungen; Review- und Freigaberegeln fehlen
- **Retry/Timeout:** nicht anwendbar beziehungsweise nicht dokumentiert

### Label-Studio-Export → Ground Truth

- **Quelle/Ziel:** `label_studio_export.json` → dokumentweise JSON-/CSV-Struktur
- **Auslöser:** manueller Skriptlauf
- **Mechanismus:** lokale Python-Verarbeitung
- **Relevante Regeln:** Dokument-ID aus Bildpfad; Werte werden typabhängig normalisiert; Sicherheiten folgen der ursprünglichen Array-Reihenfolge
- **Fehlerweg:** fehlerhafte oder fehlende Strukturen können den Lauf abbrechen; kein transaktionaler Austausch und kein Schemavertrag vorhanden
- **Versionierung:** im Skript als V7-Fix bezeichnet, aber ohne formales Datenformatschema

### Ground Truth + Prognose → Bericht

- **Quelle/Ziel:** `data/eval` und `data/processed` → JSON-/HTML-Bericht
- **Auslöser:** manueller CLI-Aufruf von `src/eval/run_eval.py`
- **Mechanismus:** Pandas, RapidFuzz/Levenshtein und python-dateutil
- **Metriken:** normalisierte WER, Feld-Precision/Recall/F1 sowie strikter und diagnostischer Tabellenvergleich
- **Fehlerweg:** fehlende Dokumente, Felder oder Tabellen werden in Teilmetriken sichtbar; feste Exit-Gates sind nicht dokumentiert
- **Monitoring:** datierte Dateien, keine zentrale Überwachung oder CI

## Sicherheits- und Datenschutzgrenzen

Das öffentliche Repository enthält Datenklassen, die als personenbezogen und finanziell sensibel behandelt werden müssen, solange synthetische Herkunft oder wirksame Anonymisierung nicht belegt sind. Der Code besitzt keine Zugriffskontrolle, Verschlüsselung, Löschfristen, Redaction oder Secret-Verwaltung; Schutz hängt vollständig von Dateisystem, Git-Hosting und Arbeitsweise ab.

Vor weiterer Nutzung sind mindestens erforderlich:

- Datensatzinventar mit Herkunft, Freigabe, Schutzklasse und Aufbewahrung,
- automatischer Scan auf direkte und indirekte Identifikatoren,
- getrennte private Datenablage statt Git für nicht öffentliche Rohdaten,
- bereinigter synthetischer Beispieldatensatz für Tests und Demos,
- dokumentiertes Lösch- und Incident-Verfahren einschließlich Git-Historie und Forks.

## Betrieb und Reproduzierbarkeit

Ein versioniertes Abhängigkeitsmanifest und eine vollständige Setup-Anleitung fehlen. Die vorhandene lokale virtuelle Umgebung ist kein reproduzierbarer Nachweis. Es gibt keine CI, keine automatisierten Tests, kein Container-Image und keinen dauerhaften Dienst.

Der zuletzt versionierte Bericht dokumentiert einen historischen Evaluationslauf. Er belegt weder unveränderte Abhängigkeiten noch einen heute reproduzierbaren Lauf. Für einen belastbaren Nachweis müssen Python-Version, Paket-Lock, Datensatzrevision, Pipeline-Revision, Konfiguration, Kommando und Ergebnis gemeinsam erfasst werden.

## Sicherung und Wiederherstellung

Git enthält derzeit Code, Ground Truth, abgeleitete Daten und Berichte. Das ist Versionsverwaltung, aber kein geeigneter Sicherungs- oder Datenschutzweg für möglicherweise sensible Rohdaten. Ein getrenntes Backupziel, Aufbewahrung, RPO/RTO und Restore-Test sind nicht dokumentiert.

## Technische Entscheidungen und offene Punkte

- Dateibasierte Übergaben sind für einen kleinen Forschungsstand einfach nachvollziehbar, benötigen aber Schemas, atomare Läufe und Datenklassifizierung.
- WER, Feld-F1 und Tabellenvergleich trennen unterschiedliche Fehlerklassen; fachkritische Felder brauchen zusätzlich eigene Schwellen und Fehlerkosten.
- Der diagnostische Best-Permutation-Vergleich hilft bei vertauschten Spalten, darf den strengeren Produktionsnachweis nicht ersetzen.
- Abhängigkeiten, Modellversionen, Label-Studio-Version und Datenformat müssen versioniert werden.
- Generierte `__pycache__`-Dateien sind teilweise bereits versioniert; ein unversionierter weiterer Cache wurde bei der Prüfung bewusst nicht verändert.
