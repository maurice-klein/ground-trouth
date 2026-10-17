# Ground Truth für die IDP-Evaluation

Dieses Repository enthält eine lokale Auswertungsstrecke für die Bachelor-IDP-Pipeline. Sie vergleicht extrahierte Kreditvertragsdaten mit einem manuell aufbereiteten Referenzbestand und erzeugt aggregierte Qualitätsberichte.

## Einstieg

- [Fachliche Dokumentation](docs/fachlich.md)
- [Technische Dokumentation](docs/technisch.md)
- Zentrale Konfiguration: `configs/base.yaml`
- Evaluationslauf: `src/eval/run_eval.py`

## Wichtige Grenze

Das Repository ist öffentlich. Die Herkunft, Freigabe und vollständige Anonymisierung der versionierten Dokument- und Ground-Truth-Bestände ist im geprüften Stand nicht dokumentiert. Bis diese Frage geklärt ist, dürfen Datensätze und abgeleitete Inhalte nicht als frei veröffentlichbare Testdaten behandelt werden. Konkrete Personen-, Vertrags-, Konto- oder Betragswerte gehören nicht in Dokumentation, Issues oder externe Berichte.

## Reproduzierbarkeit

Der Code beschreibt Ingestion, Bildvorverarbeitung, Label-Studio-Konvertierung und Evaluation. Ein versioniertes Abhängigkeitsmanifest, eine durchgehende Ausführungsanleitung und automatisierte Tests fehlen derzeit. Vor einer erneuten Ausführung müssen deshalb Laufzeit, Paketversionen und Datenfreigabe geklärt werden.
