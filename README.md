# Linux Desktop — Flock, Pup & 3D-kubus

Boids als bewegende achtergrond, een kleine hond op een XFCE/Polybar-paneel en optioneel een 3D-werkruimtekubus met een compact glazen Alt + Tab-menu. Gebaseerd op de werkende Xubuntu-installatie van november 2026, voor X11.

- **Flock: ON/OFF** naast **Pup: ON/OFF**; klikken schakelt ze om.
- Hover over Flock voor direct beschikbare schuifregelaars: aantal (16–600), snelheid, afstand houden, richting volgen, bij elkaar blijven, zichtafstand, grootte en FPS. Instellingen blijven lokaal bewaard.
- De flock blijft onder apps en boven de wallpaper. Desktopiconen blijven aanklikbaar. Richtingsbesturing laat vogels met behouden snelheid wegdraaien van de rand, in plaats van tegen de grens af te remmen. Ze blijven onder het paneel en binnen het scherm.
- Automatisch pauzeren na twee seconden volledig bedekt/fullscreen; hervatten zodra de desktop zichtbaar is. Op batterij maximaal 18 FPS.
- Pup heeft beweging, slapen, interacties en een eigen rechtermuismenu. De paneelknop start/stopt het bestaande hondproces.
- De optionele volledige paneelconfig bevat ook de bestaande snelle hovermenu's voor geluid, wifi en Bluetooth en verbergt het paneel bij fullscreen.

## Nieuw op 8 november 2026

- [3D-kubus en glazen Alt + Tab](workspace/README.md): vier vlakken, draaien met Ctrl + Alt + pijlen, vrij draaien met de muis en een Rofi-menu met uitsluitend icoontjes. Compact matglas met echte achtergrondvervaging vervangt de knipperende Compiz-switcherrand. De vaste 16:9-menuvorm is vervallen.
- [Desktop-snelkoppelingen](desktop/README.md): Word/PowerPoint online, Google Chrome en Immich met hun eigen iconen. LibreOffice Impress was al aanwezig en krijgt geen desktopstarter.
- Het eerdere Shift + touchpad-scroll-experiment is volledig teruggedraaid. Er wordt geen touchpad-remapper meegeleverd.

De kubus is een **afzonderlijke, optionele** installatie. De bestaande Flock/Pup-installer hieronder activeert geen andere windowmanager.

## Installeren

Vereist XFCE **X11**, Python 3, PyQt5, GI/GTK 3/PangoCairo, Pillow, libX11 en libXfixes. Voor de volledige paneelconfig ook Polybar, Rofi, xdotool, FontAwesome, NetworkManager/nmcli, Blueman, PipeWire/wpctl/pw-dump/pw-metadata en notify-send.

Installeer benodigde systeempakketten via je distributie. Installeer daarna alleen de apps en bedieningsscripts:

```sh
python3 install.py
bash ~/.local/share/panel-pup/download_assets.sh brown
python3 ~/.local/share/panel-pup/panel_pup.py --check
```

Dit kopieert broncode naar `~/.local/share/`, schrijft autostartbestanden en installeert de twee bedieningsscripts in `~/.local/bin/`. Bestaande Pup-instellingen worden behouden. Er worden geen processen gestart of systeeminstellingen gewijzigd. Meld opnieuw aan of start de apps zelf om ze te gebruiken. Download eerst de hondensprites; zonder sprites kan Pup niet starten.

**Volledig voorbeeldpaneel:** bekijk eerst `panel/config/polybar/config.ini` en pas zo nodig de Pup-loopruimte aan. Deze optie vervangt je Polybar/Rofi-configuratie en maakt herstelback-ups:

```sh
python3 install.py --panel
```

Dit activeert de paneelmodules, hovermenu's en paneel-autostart. Je bestaande processen blijven draaien tot je ze herstart of opnieuw inlogt. Alleen de apps installeren voegt de modules/hoverbediening niet toe aan een willekeurig bestaand paneel; gebruik daarvoor de voorbeeldconfiguratie als integratiebasis. Rootrechten zijn niet nodig voor deze installer.

Pup-configuratie: `~/.local/share/panel-pup/config.json`. Kies een lege paneelstrook; de voorbeeldcoördinaten zijn bedoeld voor een scherm van 1920 pixels breed. Flock-instellingen: `~/.config/desktop-boids/settings.json`; die worden automatisch aangemaakt. Pup start bij aanmelden en de knop stopt/start het proces in de huidige sessie. Flock onthoudt ook de aan/uitvoorkeur.

## Onderdelen en herstel

- `boids/`: simulatie, voorgebouwde instellingenpopup en gevalideerde voorkeuren.
- `panel-pup/`: hondapp, gedragstests en downloadhelper voor sprites.
- `panel/`: integratie met Polybar/Rofi, beide aan/uitbedieningen en hoverwatcher.
- `workspace/`: optionele Compiz-configuratie, glazen Rofi-switcher en installatie met back-ups.
- `desktop/`: portable installatie van de vier desktopstarters en officiële icoondownloads.
- `install.py`: installatie met back-ups; `--home` laat een geïsoleerde testinstallatie toe.

De installer meldt waar de back-ups staan. Paneelbestanden die door de bestaande paneelinstaller zijn vervangen kunnen worden hersteld met `python3 ~/.local/share/linux-desktop/panel/restore.py PAD_NAAR_BACKUP`. Daarna Polybar en de hoverwatcher herstarten.

De code gebruikt geen cloudservice, account of betaalde API. Lokaal opgeslagen voorkeuren, crashrapporten, backups en bestaande afbeeldingen worden niet met deze repository meegeleverd.

## Artwork en licentie

De bestaande Panel Pup-code heeft zijn MIT-licentie in `panel-pup/CODE_LICENSE.txt`. Die licentie geldt niet voor hondensprites. De downloadhelper haalt originele sprites op uit [VS Code Pets](https://github.com/tonybaloney/vscode-pets), met attributie aan NVPH Studio en de bijbehorende artworklicentie (CC BY-ND 4.0). Lokale bewerkte sprites worden niet gedistribueerd. Mandanimaties zijn optioneel; zonder die bestanden gebruikt Pup de gewone slaapstand.

## Controle

Syntax, Pup-gedragstests en een geïsoleerde installatie kunnen lokaal worden gecontroleerd. De actieve Xubuntu-versie is handmatig getest op hoverbediening, echte desktopklikken, het openen/sluiten van een map, de stabiele desktoplaag en pauzeren/hervatten bij fullscreen. Dit is geen garantie voor andere windowmanagers, meerdere schermen of Wayland. De flight area gebruikt momenteel het primaire scherm.

Randbesturing bijgewerkt op 2 november 2026: hoekverandering per frame is begrensd, ook bij een frontale nadering van een rand. Head-on- en hoektests controleren verschillende snelheden en 10/24 FPS. Een integratiecontrole met de echte flockstap en 160 vogels simuleerde 60 seconden zonder harde grensbotsingen.

```sh
python3 -m unittest discover -s boids/tests -v
python3 -m unittest discover -s panel-pup/tests -v
```

Rendering geoptimaliseerd op 2 november 2026: vogelvormen worden vooraf in 64 richtingen per kleur getekend en daarna als kleine transparante sprites hergebruikt. Een lokale offscreen-tekenbenchmark met 600 vogels daalde van circa 12 naar 3 ms per frame; dit is alleen de tekenfase, niet een meting van het totale CPU-verbruik. De batterijlimiet is 18 FPS, zodat een gekozen instelling zoals 17 FPS niet stilzwijgend op 10 FPS blijft steken.
