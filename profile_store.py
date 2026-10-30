"""Panda3D profile, with conservative migration and atomic backup recovery.

The old save.json is read only. Campaign position is never inferred from a lesson.
"""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import shutil
import sys
from fortress import restore_towers
from persistence import validate as legacy_validate


ROOT = Path(__file__).resolve().parent
PROFILE_PATH = (Path(os.environ.get("APPDATA",str(Path.home())))/"LeadTheTarget"/"profile3.json"
                if getattr(sys,"frozen",False) else ROOT/"profile3.json")
DEFAULTS = {"resolution":[1280,800],"display_mode":"Windowed","fps":60,"vsync":True,
            "compact":False,"large_text":False,"reduced_motion":False,"high_contrast":False,
            "muted":False,"volume":.4}
RESOLUTIONS = ((960,600),(1024,768),(1280,720),(1280,800),(1366,768),(1600,900),
               (1920,1080),(2560,1440),(3840,2160))
FPS_OPTIONS = (30,60,90,120,144,165,240,0)


def finite(value,default,low,high):
    return min(high,max(low,value)) if type(value) in (int,float) and math.isfinite(value) else default


def settings(raw):
    result = deepcopy(DEFAULTS)
    if not isinstance(raw,dict): return result
    for key in ("compact","large_text","reduced_motion","high_contrast","muted","vsync"):
        result[key] = raw.get(key,result[key]) is True
    res = raw.get("resolution")
    if isinstance(res,(tuple,list)) and len(res)==2 and all(type(v) is int for v in res):
        result["resolution"] = [int(finite(res[0],1280,800,3840)),int(finite(res[1],800,600,2160))]
    if raw.get("display_mode") in ("Windowed","Borderless","Fullscreen"):
        result["display_mode"] = raw["display_mode"]
    if type(raw.get("fps")) is int and raw["fps"] in FPS_OPTIONS: result["fps"] = raw["fps"]
    result["volume"] = finite(raw.get("volume"),.4,0,1)
    return result


def validate(raw):
    if not isinstance(raw,dict) or raw.get("schema") != 3: return {}
    c = raw.get("campaign",{})
    if not isinstance(c,dict): c = {}
    towers = restore_towers(c.get("towers",[]))
    completed = c.get("completed",{})
    completed = {k:int(finite(v,1,1,16)) for k,v in completed.items()
                 if k.isdigit() and 1<=int(k)<=100 and type(v) is int} if isinstance(completed,dict) else {}
    a = raw.get("academy",{})
    a = legacy_validate(a) if isinstance(a,dict) else {}
    return {"schema":3,"campaign":{"level":int(finite(c.get("level"),1,1,100)),
            "credits":int(finite(c.get("credits"),160,0,1000000)),
            "site":int(finite(c.get("site"),0,0,100000)),"completed":completed,
            "towers":[t.snapshot() for t in towers]},"academy":a,
            "settings":settings(raw.get("settings")),
            "records":{k:{"health":int(finite(v.get("health"),1,1,16)),
                          "shots":int(finite(v.get("shots"),0,0,100000)),
                          "seconds":finite(v.get("seconds"),0,0,10000)}
                       for k,v in raw.get("records",{}).items()
                       if k.isdigit() and 1<=int(k)<=100 and isinstance(v,dict)}
                if isinstance(raw.get("records"),dict) else {}}


def load(path=PROFILE_PATH):
    for candidate in (path,path.with_suffix(".json.bak")):
        try:
            data = validate(json.loads(candidate.read_text(encoding="utf-8")))
            if data: return data, "Recovered backup profile." if candidate != path else ""
        except (OSError,ValueError,TypeError): pass
    legacy = ROOT/"save.json"
    try:
        old = legacy_validate(json.loads(legacy.read_text(encoding="utf-8")))
        if old:
            prefs = {**old.get("settings",{}),"resolution":old.get("settings",{}).get("window",[1280,800])}
            return {"schema":3,"campaign":{"credits":max(160,old["currency"])},
                    "academy":old,"settings":settings(prefs),"records":{}}, "Academy, credits and preferences imported. Campaign begins at level 1; original save kept."
    except (OSError,ValueError,TypeError): pass
    return {"schema":3,"campaign":{},"academy":{},"settings":deepcopy(DEFAULTS),"records":{}}, ""


def save(profile,path=PROFILE_PATH):
    try:
        data = validate(profile)
        if not data: return False
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():
            try: good = bool(validate(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError,ValueError,TypeError): good = False
            shutil.copy2(path,path.with_suffix(".json.bak" if good else ".json.unreadable"))
        temp = path.with_suffix(".json.tmp")
        with temp.open("w",encoding="utf-8") as stream:
            json.dump(data,stream,indent=2,allow_nan=False); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp,path)
        return True
    except (OSError,ValueError,TypeError): return False
