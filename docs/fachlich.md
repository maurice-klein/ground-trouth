# Fachliche Dokumentation

## Problem und Ziel

Die IDP-Pipeline soll Kreditvertragsdokumente nicht nur technisch verarbeiten, sondern ihre Extraktionsqualität gegen einen nachvollziehbaren Referenzbestand messen. Dieses Repository stellt dafür Ground Truth, Normalisierungsregeln und aggregierte Evaluationsberichte bereit.

Der fachliche Nutzen liegt in drei getrennten Qualitätsaussagen:

- OCR-Qualität als Word Error Rate,
- Qualität strukturierter Felder als Precision, Recall und F1,
- Qualität erkannter Tilgungsplantabellen als strikter Zellvergleich und diagnostischer Vergleich bei vertauschten Spalten.

## Rollen

- **Annotierende Person:** markiert relevante Inhalte in Label Studio und prüft die Zuordnung zum Dokument.
- **Pipeline-Entwicklung:** erzeugt OCR-, Feld- und Tabellenergebnisse aus denselben Dokumenten.
- **Evaluierende Person:** konvertiert Annotationen, startet die Auswertung und interpretiert aggregierte Fehlerbilder.
- **Review:** entscheidet, ob Datenfreigabe, Metriken und Ergebnisdarstellung für den vorgesehenen Zweck ausreichen.

## Geschäftsprozess: Referenzbestand erstellen und auswerten

### Auslöser

Eine neue oder geänderte Extraktionspipeline soll gegen einen festgelegten Dokumentbestand bewertet werden.

### Eingaben

- Dokumentseiten beziehungsweise daraus erzeugte Bilder,
- manuelle Label-Studio-Annotationen,
- OCR-Texte, extrahierte Felder und erkannte Tabellen der Pipeline,
- Konfiguration für Vorverarbeitung, OCR, Layout und Metriken.

### Ablauf

1. Dokumente werden in Seitenbilder überführt und optional vorverarbeitet.
2. Eine annotierende Person markiert Felder und Tabellenbereiche in Label Studio.
3. Das Konvertierungsskript gruppiert Annotationen dokumentweise und normalisiert ausgewählte Werte.
4. Die Pipeline-Ergebnisse werden mit dem Referenzbestand verglichen.
5. Die Auswertung erzeugt eine maschinenlesbare Zusammenfassung und einen HTML-Bericht.
6. Abweichungen werden nach OCR, Feldern und Tabellen getrennt bewertet; Verbesserungen an Pipeline oder Annotationen lösen einen neuen Lauf aus.

### Ergebnis

Ein datierter Bericht mit aggregierten Qualitätsmetriken und Detailansichten pro Dokument oder Feld. Der zuletzt versionierte Bericht belegt einen historischen Lauf, aber keinen aktuellen automatisierten Qualitäts-Gate.

### Fehlerfälle

- Referenz- und Vorhersageordner stimmen nicht überein.
- Annotationen fehlen, sind leer oder einem falschen Dokument zugeordnet.
- Feldwerte benötigen eine nicht dokumentierte Normalisierung.
- Eine Tabelle wird nicht gefunden oder ihre Spalten sind vertauscht.
- Paket- und Modellversionen sind nicht reproduzierbar festgelegt.
- Der Datensatz besitzt keine belegte Veröffentlichungs- oder Verarbeitungsfreigabe.

## Daten- und Freigabegrenze

Der Code verarbeitet potenziell hochsensible Vertrags- und Identifikationsfelder, darunter Namen, Adressen, Vertragsnummern, IBAN/BIC, Beträge, Laufzeiten und Sicherheiten. Das Repository ist öffentlich. Im geprüften Stand ist nicht dokumentiert, ob sämtliche versionierten Daten synthetisch, wirksam anonymisiert oder anderweitig zur Veröffentlichung freigegeben sind.

Bis zur Klärung gilt:

- keine konkreten Werte in Wiki, Tickets, Präsentationen oder öffentliche Berichte übernehmen,
- keine neuen Roh- oder Zwischenstände pushen,
- Herkunft, Rechtsgrundlage beziehungsweise Freigabe und Anonymisierung je Datensatz dokumentieren,
- bei echten personenbezogenen Daten Veröffentlichung stoppen und eine bereinigte Historie als gesonderte Sicherheitsmaßnahme planen.

## Offene fachliche Fragen

- Wem gehört der Referenzbestand und für welchen Zweck darf er verwendet werden?
- Sind alle Dokumente nachweislich synthetisch oder vollständig anonymisiert?
- Welche Qualitätsgrenzen gelten für OCR, Felder und Tabellen, und wer gibt sie frei?
- Welche Fehler sind für den späteren Fachprozess kritisch, auch wenn eine Gesamtmetrik gut aussieht?
- Wie werden Annotationen versioniert, reviewed und gegen unbeabsichtigte Änderungen geschützt?
