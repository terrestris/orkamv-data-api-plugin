This plugin loads geopackage files from the ORKA.MV DATA API.

Installation
============

1. Im QGIS Reiter Erweiterungen den Menüpunkt `Erweiterungen verwalten und installieren` auswählen.
1. Oben links `Alle Erweiterungen` auswählen und dort nach `ORKa.MV Data API` suchen. Das Plugin mit Klick auf `Erweiterung installieren` (unten rechts) installieren.

Anwendung
=========

1. Im Feld Server URL die URL zu der Data API angeben, inklusive dem API-Endpunkt (`/api`).
1. Zur Auswahl des Kartenausschnitts, der in ein GeoPackage exportiert werden soll, neben der Textanzeige für den Kartenausschnitt die 3 Punkte `...` anklicken und dort die gewünschte Eingabemethode wählen.
1. Alle Icons, die zur Darstellung der Daten in dem Geopackage benötigt werden, werden in das angegebene SVG Verzeichnis integriert. Dabei werden vorhandene Daten Überschrieben. In den QGIS Einstellungen kann ein neues SVG Verzeichnis hinzu gefügt werden. Dazu suchen Sie in den Einstellungen (`Einstellungen` -> `Optionen`) oben links nach `SVG` und tragen unter `SVG-Pfade` ein neues Verzeichnis ein.
1. Wenn unter Speicherung `Temporär` ausgewählt wird, dann werden das Geopackage und die Styles im temporären Verzeichnis des Betriebssystems abgelegt und ggf. beim nächsten Start gelöscht.
1. Wenn unter Speicherung `Verzeichnis` ausgewählt wird, muss ein Verzeichnis für das Geopackage und die Styles ausgewählt werden.
1. Mit Klick auf Starten startet der Prozess. Achten Sie ggf. auf Meldungen die in der QGIS PushBar erscheinen.
