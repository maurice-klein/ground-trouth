# Datensatz-Governance und Herkunftsnachweis

## Zweck und Geltungsbereich

Diese Regel gilt für den Referenzbestand unter `data/eval/`, die zugehörigen Label-Studio-Exporte und jede daraus abgeleitete neue Datensatzversion. Sie verhindert, dass reale Vertragsdaten oder nicht nachvollziehbare Änderungen unbemerkt in das öffentliche Repository gelangen.

Der aktuell versionierte Bestand umfasst zwölf synthetische Kreditverträge. Maurice bestätigte den synthetischen Status des vollständigen Bestands am 17.10.2026. Der ursprüngliche Generator beziehungsweise manuelle Erstellungsweg, seine Version und die Label-Studio-Version sind für diesen historischen Bestand nicht mehr belegt; diese Angaben bleiben ausdrücklich `unknown` und werden nicht nachträglich erfunden.

## Führender Nachweis

`data/eval/dataset-card.json` ist die maschinenlesbare Datensatzkarte. Sie hält mindestens fest:

- Datensatz-ID und Version,
- synthetischen Status, Bestätiger und Bestätigungsdatum,
- Umfang und enthaltene Datenklassen,
- Git-Revision und Git-Tree des geprüften Bestands,
- Ursprungsexporte und ihre Git-Blob-IDs,
- Erstellungs- und Annotationswerkzeuge samt Version, soweit belegt,
- Reviewstatus, Einschränkungen und offene Nachweise.

Git-Objekt-IDs binden die Karte an den geprüften Inhalt. Sie sind Integritätsreferenzen innerhalb der Git-Historie, aber weder ein unabhängiges Backup noch ein Restore-Nachweis.

## Freigabe einer neuen Version

Eine Datensatzänderung wird nur in derselben Änderung wie die aktualisierte Datensatzkarte übernommen. Der Review prüft:

1. Alle Dokumente, Annotationen und Werte wurden synthetisch erzeugt; reale Dokumente oder aus realen Personen abgeleitete Identifikatoren sind ausgeschlossen.
2. Generator, Prompt oder manuelles Verfahren, verantwortliche Person, Erstellungsdatum und verwendete Versionen sind nachvollziehbar festgehalten.
3. Roh- und Ground-Truth-Dateien lassen sich über eine stabile Dokument-ID zuordnen; Umbenennungen und ausgeschlossene Dokumente sind erklärt.
4. JSON- und CSV-Strukturen sind syntaktisch gültig. Sobald Schemas vorhanden sind, müssen sie zusätzlich bestehen.
5. Eine zweite Person oder ein ausdrücklich benannter Review prüft Stichproben fachlich und bestätigt den synthetischen Status.
6. Datensatzkarte, Git-Revision beziehungsweise Tree-Referenz und abgeleitete Berichte werden gemeinsam aktualisiert. Qualitätsberichte dürfen nicht als Freigabe der Herkunft missverstanden werden.

## Fehler- und Incidentweg

Bei unklarer Herkunft wird die Änderung nicht freigegeben. Bei Verdacht auf reale Daten wird die Verarbeitung gestoppt, der betroffene Stand nicht weiter verteilt und der Vorfall mit Repository-Owner und Datenschutzverantwortung bewertet. Ein versehentlicher Commit realer Daten erfordert eine bewusste Bereinigung der Git-Historie und Prüfung vorhandener Klone oder Forks; ein normales Löschen in einem Folgecommit genügt nicht.

## Offene Nachweise

- Ursprünglicher Generator oder manueller Erstellungsweg der zwölf historischen Verträge
- Version und Konfiguration der verwendeten Label-Studio-Instanz
- formale JSON-/CSV-Schemas und automatisierter Validator für Datensatzkarte und Ground Truth
- festgelegte fachliche Qualitätsgrenzen und verantwortliche Freigaberolle
- unabhängiger Backup-, Aufbewahrungs- und Restoreweg
