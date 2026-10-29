# Third-party components

The runtime uses pygame 2.6.1, including its bundled SDL libraries and default
font. Pygame's installed distribution supplies its own licences and notices.
Its LGPL text is copied into the packaged release as `PYGAME-LGPL.txt`.

- Pygame project and source: https://github.com/pygame/pygame
- Pygame licence information: https://www.pygame.org/LGPL
- Python runtime source and licence: https://www.python.org/downloads/source/
- PyInstaller build tool and bootloader notices: https://github.com/pyinstaller/pyinstaller

The screenshot references informed the visual direction. The game draws original
procedural UI/mesh artwork; no pixels or commercial asset sheets were extracted.
Audio cues are generated locally. Body text uses an available system font; titles
use pygame's bundled font. No font is fetched from a remote service.
