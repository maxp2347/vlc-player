# VLC Player — Python

Petit lecteur vidéo multiplateforme basé sur le moteur **libVLC** (VLC), avec une
interface **Tkinter**. Fonctionne sur **Windows, macOS et Linux**.

Fonctionnalités : ouverture de fichiers vidéo (mp4, mkv, avi, mov, webm…),
lecture/pause, stop, barre de progression, volume, plein écran (double-clic),
raccourcis clavier (Espace, ←/→ ±5 s, Échap).

### Projets (machine lecteur dédiée)

Au lancement, l'app propose : **Nouveau projet**, **Charger un projet** ou
**Continuer sans projet**. Un projet définit :

- **Nom** et **emplacement** du fichier projet (`<nom>.vlcproj.json`)
- **Moniteur** de sortie (détection automatique des écrans)
- **Résolution** et **fréquence d'affichage** voulues
- **Décodeur** : GPU (accéléré) ou CPU (`--avcodec-hw`)
- **Carte son** / sortie audio (détection PulseAudio/ALSA sous Linux, modules
  WASAPI/DirectSound sous Windows)

Au lancement du projet, l'application **applique les réglages hardware** :
changement de résolution/fréquence (Windows `ChangeDisplaySettingsEx`, Linux
`xrandr`, macOS `displayplacer`), fenêtre positionnée sur le moniteur choisi,
instance libVLC recréée avec le décodeur et la sortie audio choisis. La
résolution d'origine est **restaurée à la fermeture**.

> **Limites plateformes** : sous Linux, le changement de mode nécessite X11
> (xrandr) — sous Wayland, un avertissement s'affiche ; sous macOS, installez
> `displayplacer` (brew) pour le changement de résolution ; le choix d'un
> périphérique audio précis est disponible via ALSA (Linux) et les modules de
> sortie (Windows), l'énumération fine des périphériques dépend du système.

### Menu Média

Le menu **Média** donne accès à :

- **Importer des médias…** — ajout de vidéos/images à la liste du projet.
  Si la définition ou la fréquence d'images d'un média diffère du projet
  (résolution ou fps), une **alerte** s'affiche avec choix « Continuer » ou
  « Ignorer pour ce projet » (le choix est mémorisé par média).
- **Gérer les médias…** — liste des médias du projet avec :
  - **points d'entrée/sortie** : lancez le média, placez la lecture à l'endroit
    voulu puis « Début ici » / « Fin ici » (la lecture s'arrête au point de
    sortie et enchaîne sur le média suivant) ;
  - **volume par points** : la bande sous la vidéo affiche un waveforme
    (réel si `ffmpeg` est installé, sinon ligne de base) avec la courbe de
    volume en jaune — clic pour ajouter/déplacer un point, clic droit pour
    supprimer. Bouger le curseur de volume pendant la lecture crée
    automatiquement un point à la position courante ; le volume est
    interpolé entre les points.
- **Générer une mire…** — mires de test :
  - **statiques** (PNG) : barres SMPTE, grille, échelle de gris, focus,
    couleurs pleines (rouge/vert/bleu/blanc/noir) ;
  - **dynamiques** (AVI MJPEG généré par l'app, sans dépendance externe) :
    barre défilante, damier clignotant, cercle rotatif — avec choix de la
    taille (720p à 4K), de la fréquence d'images (25/30/50/60 ips), de la
    fréquence du motif (Hz) et de la durée.

### Réglages machine (mode lecteur dédié)

Un panneau **⚙ Réglages** dans l'application permet de configurer les réglages
de base de la machine lecteur, sauvegardés automatiquement :

- **Volume par défaut** au démarrage
- **Lecture en boucle**
- **Reprise de la dernière vidéo** au lancement
- **Plein écran au démarrage** (mode kiosque)
- **Anti-veille** : empêche la mise en veille de la machine et de l'écran
  pendant la lecture —
  - Windows : `SetThreadExecutionState`
  - macOS : `IOPMAssertion` (IOKit)
  - Linux : `systemd-inhibit`, sinon `gsettings` (GNOME, valeur restaurée à la sortie)

Les réglages sont stockés dans un fichier JSON :

- Windows : `%APPDATA%\VLCPlayer\settings.json`
- macOS : `~/Library/Application Support/VLCPlayer/settings.json`
- Linux : `~/.config/VLCPlayer/settings.json` (ou `$XDG_CONFIG_HOME`)

## Prérequis

- **Python 3.9+**
- **VLC media player** installé sur la machine (fournit la bibliothèque native `libvlc`) :
  - Windows : [videolan.org/vlc](https://www.videolan.org/vlc/) (installateur 64 bits)
  - macOS : `brew install --cask vlc` ou l'installateur officiel
  - Linux (Debian/Ubuntu) : `sudo apt install vlc`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Exécution locale

```bash
python main.py
```

## Tests

```bash
# Tests logiques (sans écran requis) : réglages, projets, mires/AVI, enveloppe volume…
python3 tests/test_app.py

# Test GUI (machine avec écran, Tk et VLC installés) :
# ouvre l'app et chaque dialogue séquentiellement
python3 tests/smoke_gui.py
```

## Construire l'exécutable (PyInstaller)

Scripts fournis :

```bash
./build.sh        # Linux / macOS
build.bat         # Windows (double-clic ou invite de commandes)
```

Ou manuellement :

```bash
pyinstaller --noconfirm --windowed --onefile --name VLCPlayer main.py
```

L'exécutable est généré dans `dist/VLCPlayer` (ou `dist\VLCPlayer.exe`).

> **Note** : par défaut, l'exécutable recherche VLC installé sur la machine cible
> (python-vlc charge `libvlc` automatiquement). Pour un build **entièrement
> autonome**, ajoutez les bibliothèques natives :
>
> - **Windows** :
>   `--add-binary "C:\Program Files\VideoLAN\VLC\libvlc.dll;." --add-binary "C:\Program Files\VideoLAN\VLC\libvlccore.dll;." --add-data "C:\Program Files\VideoLAN\VLC\plugins;plugins"`
> - **macOS** :
>   `--add-binary "/Applications/VLC.app/Contents/MacOS/lib/libvlc.dylib:." --add-binary "/Applications/VLC.app/Contents/MacOS/lib/libvlccore.dylib:." --collect-data /Applications/VLC.app/Contents/MacOS/plugins`
> - **Linux** :
>   `--add-binary "/usr/lib/x86_64-linux-gnu/libvlc.so*:." --add-binary "/usr/lib/x86_64-linux-gnu/libvlccore.so*."`

Chaque build doit être fait **sur** la plateforme cible (PyInstaller ne fait pas
de compilation croisée).

> **Note** : si vous clonez ce dépôt sous Linux/macOS, rendez le script exécutable
> après le clone : `chmod +x build.sh` (le bit exécutable n'est pas préservé par
> l'envoi via API).

## Limitations connues

- **macOS** : l'incrustation de la vidéo dans une fenêtre Tk n'est pas supportée
  par libVLC ; la vidéo s'ouvre dans une fenêtre VLC dédiée, les contrôles
  restent dans la fenêtre principale.
