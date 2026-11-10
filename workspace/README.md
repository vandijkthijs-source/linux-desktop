# 3D-kubus en glazen Alt + Tab

Werkende configuratie van 8 november 2026 voor XFCE/Xubuntu op **X11**. Compiz vervangt Xfwm4 tijdens de sessie. De bestaande Polybar, Plank en Pup blijven aparte processen. Dit onderdeel wordt alleen geïnstalleerd wanneer je de onderstaande installer zelf uitvoert; de hoofdinstaller voor Flock/Pup activeert de kubus niet.

## Benodigd

Compiz 0.9 met `compiz-plugins`, `compizconfig-settings-manager`, de Python-module `compizconfig`, `gtk-window-decorator`, het Metacity-thema **Arc-Dark**, PyQt5, xdotool, wmctrl, procps/pgrep, Python 3 en libX11. Een C-compiler (`cc`) maakt de sneltoetsaanroep extra snel; zonder compiler wordt de Python-terugval gebruikt. Beschikbaarheid/pakketnamen verschillen per distributie. Gebruik `/usr/bin/python3` zodat distributiemodules beschikbaar zijn.

## Installeren en activeren

```sh
# Alleen bestanden kopiëren; geen actieve desktop- of logininstellingen wijzigen:
python3 workspace/install.py

# Expliciet de Compiz-instellingen toepassen en aanmelden met de kubus:
/usr/bin/python3 workspace/install.py --configure --autostart

# Nu activeren, of opnieuw aanmelden:
~/.local/bin/desktop-cube-session
```

De configuratie gebruikt de Compiz **INI-backend**. De installer maakt lokale back-ups van overschreven bestanden en het bestaande Compiz-profiel, en bewaart een manifest. Bestaande andere Compiz-commando's blijven behouden; twee vrije slots worden gebruikt voor Alt + Tab. Actieve plugins Desktop Wall, de ingebouwde switchers en oude sessie-geometrie worden vervangen door deze configuratie. Andere plugins blijven behouden. Controleer bestaande sneltoetsen voor Alt + Tab in XFCE of andere tools als ze de Compiz-binding onderscheppen.

Vier horizontale vlakken vervangen de oude workspace-indeling. Test dit eerst met open werk opgeslagen en zonder vensters op extra workspaces; de installer verplaatst bestaande vensters niet tussen workspace-indelingen.

## Bediening en uiterlijk

- **Ctrl + Alt + links/rechts**: naar een andere zijde draaien.
- **Ctrl + Alt + Shift + links/rechts**: een venster meenemen.
- **Ctrl + Alt + slepen met linkermuisknop**: vrij draaien.
- **Alt + Tab** en **Alt + Shift + Tab**: vooruit/achteruit kiezen; Alt loslaten kiest het venster, Escape annuleert.

De kubus heeft effen donkere boven-/onderkanten, een donkere achtergrond en een subtiele reflectie. De huidige Alt + Tab-opmaak is compact, ongeveer **324 × 108 pixels**, met uitsluitend icoontjes, afgeronde hoeken, een zachte lichte glaslaag en achtergrondvervaging. De eerdere vaste 16:9-verhouding is vervallen. De grootte kan veranderen met meer vensters of andere schaalinstellingen.

De standaard Compiz-switchers tekenden bij herhaald schakelen een steeds dikkere/knipperende rand. De eerste vervanging gebruikte Rofi; de definitieve versie gebruikt een **vooraf geladen PyQt5-menu** om de opstartvertraging bij elke Alt + Tab weg te nemen. App-icoontjes blijven in het geheugen. Een minimale C-aanroep verstuurt alleen een lokaal socketbericht; de Python-client kan de service starten als die nog niet draait. Op de actieve laptop verscheen het menu in korte toetsproeven na ongeveer 70–80 ms, inclusief aanroep en controle; dit is geen garantie voor andere systemen.

De lichte glasvervaging is beperkt tot `class=DesktopAltTab & title=Desktop Alt Tab`. De selectie heeft een duidelijke blauwe rand en bijna wit vlak. De service blijft op de achtergrond beschikbaar, maar leest Alt en grijpt het toetsenbord uitsluitend zolang het menu open is. Escape annuleert en geeft het toetsenbord meteen terug; loslaten van Alt kiest het venster. Er worden geen muis- of toetsmappings gewijzigd. Eén korte rustcontrole mat nul extra CPU-ticks in één seconde; het geheugenverbruik op dat moment staat niet vast voor andere systemen. Met `--autostart` worden zowel de kubus als de menuservice bij aanmelden klaargezet.

`desktop-cube-session` voorkomt dubbele Compiz-processen en start Xfwm4 als Compiz stopt. Dit vangt een afgesloten/gecrashte Compiz op; het is geen watchdog voor een vastgelopen compositor.

## Herstellen

Schakel eerst de kubus bij aanmelden uit en ga terug naar Xfwm4:

```sh
rm -f ~/.config/autostart/desktop-cube.desktop ~/.config/autostart/desktop-alt-tab-service.desktop
xfwm4 --replace
```

De sessiehelper kan daarbij zelf ook terugvallen op Xfwm4. Stop desgewenst de menuservice met een `quit`-bericht naar `$XDG_RUNTIME_DIR/desktop-alt-tab-warm.sock` voordat je die bestanden terugzet. Herstel vervolgens je gewenste Compiz-profiel uit de door de installer gemelde map `~/.local/state/desktop-cube-backups/…/compiz-1/`. Gebruik `manifest.json` om eerdere versies van de gekopieerde scripts en het Rofi-thema terug te zetten. Een manifestregel zonder eerdere back-up betekent dat het bestand nieuw was. Als je teruggaat naar Xfwm4, kun je het oude aantal workspaces weer instellen in XFCE; de kubus gebruikt één groot bureaublad met vier viewports.

## Gecontroleerd

Op de actieve laptop: Compiz geladen; toetsenbordrotatie heen/terug; vrije muisrotatie; Polybar/Pup zichtbaar; Alt + Tab vooruit/achteruit; kiezen bij loslaten van beide Alt-toetsen; stabiele menuranden na herhaald wisselen. De uiteindelijke matte glasweergave is visueel gecontroleerd. Autostart is ingesteld maar nog niet met een nieuwe reboot getest. Flock stond uit tijdens de kubuscontrole: de bewegende boids-laag onder Compiz is nog niet opnieuw bevestigd. De oudere Flock-laagtests in de hoofd-README waren onder Xfwm4. Deze nieuwe werkruimteconfiguratie is alleen op de huidige laptop toegepast.
