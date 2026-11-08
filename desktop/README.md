# Desktop-snelkoppelingen

De desktop heeft **Word**, **PowerPoint**, **Google Chrome** en **Immich**, met hun eigen iconen. Word en PowerPoint openen de webversies; Chrome gebruikt de geïnstalleerde browserlauncher. Immich opent de eigen fotobibliotheek. Op de actieve laptop blijft Immich als Chrome-appvenster openen; de portable installer hieronder opent de opgegeven Immich-URL in de standaardbrowser.

```sh
python3 desktop/install_shortcuts.py --trust
```

De installer haalt de originele Word-/PowerPoint-SVG's van Microsoft's SharePoint/Fabric-CDN en het originele Immich-logo uit de officiële Immich-repository. Logo's worden niet als bestanden in deze repository meegeleverd; Microsoft en Immich behouden hun rechten op hun merken en artwork. De download-URL's staan in de broncode. Voor een andere Immich-server geef je de eigen URL mee via `--immich-url URL`.

Bestaande bestanden krijgen lokale back-ups. `--trust` gebruikt de huidige grafische sessie om de starters betrouwbaar te markeren. Zonder die optie kan XFCE bij de eerste start om bevestiging vragen. Een offline controle kan met `--offline --home /tmp/shortcut-test`; daarbij gebruikt de installer beschikbare thema-iconen in plaats van de originele merklogo's. Als Chrome niet geïnstalleerd is, slaat hij die starter over.

**LibreOffice Impress** is al geïnstalleerd op de actieve laptop en te vinden via het toepassingenmenu. Daarvoor is geen desktopstarter toegevoegd.
