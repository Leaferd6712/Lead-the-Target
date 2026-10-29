"""Create the original application icon using the game's vector drawing code."""
import io
import os
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT","1")
import pygame
from theme import app_icon


if __name__=="__main__":
    pygame.init()
    folder=Path(__file__).resolve().parents[1]/"assets"
    folder.mkdir(exist_ok=True)
    image=app_icon()
    stream=io.BytesIO()
    pygame.image.save(image,stream,"icon.png")
    data=stream.getvalue()
    header=struct.pack("<HHH",0,1,1)+struct.pack("<BBBBHHII",0,0,0,0,1,32,len(data),22)
    (folder/"app.ico").write_bytes(header+data)
    pygame.quit()
