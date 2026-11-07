# Ground Truth für die IDP-Evaluation

Dieses Repository enthält eine lokale Auswertungsstrecke für die Bachelor-IDP-Pipeline. Sie vergleicht extrahierte Kreditvertragsdaten mit einem manuell aufbereiteten Referenzbestand und erzeugt aggregierte Qualitätsberichte.

## Einstieg

- [Fachliche Dokumentation](docs/fachlich.md)
- [Technische Dokumentation](docs/technisch.md)
- [Datensatz-Governance und Herkunftsnachweis](docs/dataset-governance.md)
- Zentrale Konfiguration: `configs/base.yaml`
- Evaluationslauf: `src/eval/run_eval.py`

## Datenstatus

Maurice hat am 17.10.2026 bestätigt, dass der vollständige Dokument- und Ground-Truth-Bestand synthetisch ist. Enthaltene Personen-, Vertrags-, Konto- und Betragswerte sind Testdaten und bilden keine realen Personen oder Verträge ab. Neue Datensätze dürfen nur aufgenommen werden, wenn dieser synthetische Charakter erhalten und nachvollziehbar dokumentiert bleibt.

Die maschinenlesbare Datensatzkarte unter `data/eval/dataset-card.json` bindet den aktuell geprüften Referenzbestand an seine Git-Revision und hält belegte sowie noch unbekannte Herkunftsangaben getrennt fest. Neue oder veränderte Datensatzversionen dürfen erst nach Aktualisierung und Review dieser Karte übernommen werden.

## Reproduzierbarkeit

Der Code beschreibt Ingestion, Bildvorverarbeitung, Label-Studio-Konvertierung und Evaluation. Ein versioniertes Abhängigkeitsmanifest, eine durchgehende Ausführungsanleitung und automatisierte Tests fehlen derzeit. Vor einer erneuten Ausführung müssen deshalb Laufzeit, Paketversionen und Datenfreigabe geklärt werden.
