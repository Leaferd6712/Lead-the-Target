"""Generate the game's original short PCM cues using only Python's standard library."""
from array import array
from math import sin,pi
from pathlib import Path
import wave


def main():
    root=Path(__file__).resolve().parents[1]/'assets';root.mkdir(exist_ok=True)
    for name,freq,duration in (('shot',360,.055),('hit',680,.11),('win',880,.24),('click',510,.045)):
        rate=22050
        samples=array('h',(int(6500*(1-i/(rate*duration))**2*sin(2*pi*freq*i/rate)) for i in range(int(rate*duration))))
        with wave.open(str(root/(name+'.wav')),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate);stream.writeframes(samples.tobytes())


if __name__=='__main__':main()
