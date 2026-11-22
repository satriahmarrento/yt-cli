#!/usr/bin/env python3
import json, os, sys, time, hashlib, random
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

BASE = os.environ.get("YTM_PREF_DIR", os.path.expanduser("~/.config/ytfzf"))
PREF = os.path.join(BASE, "preferences.json")
HISTORY = os.path.join(BASE, "history.jsonl")
CLIENT_VERSION = "1.20261117.06.00"

def load():
    try:
        with open(PREF, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"artists":{}, "seeds":{}, "queries":{}, "banned":[], "plays":{}, "skips":{}, "likes":{}}

def save(d):
    os.makedirs(BASE, exist_ok=True)
    tmp=PREF+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(d,f,ensure_ascii=False,indent=2)
    os.replace(tmp,PREF)

def search(query, timeout=20):
    payload={"context":{"client":{"clientName":"WEB_REMIX","clientVersion":CLIENT_VERSION,"hl":"en","gl":"US"}},"query":query}
    req=Request("https://music.youtube.com/youtubei/v1/search",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"})
    with urlopen(req,timeout=timeout) as r:
        data=json.load(r)
    out=[]
    def walk(x):
        if isinstance(x,list):
            for v in x: walk(v)
        elif isinstance(x,dict):
            ri=x.get("musicResponsiveListItemRenderer")
            if ri:
                pid=ri.get("playlistItemData",{}).get("videoId")
                cols=ri.get("flexColumns",[]) or []
                vals=[]
                for c in cols:
                    runs=c.get("musicResponsiveListItemFlexColumnRenderer",{}).get("text",{}).get("runs",[]) or []
                    vals.append("".join(v.get("text","") for v in runs))
                if pid:
                    artist=vals[1].split(" • ")[0] if len(vals)>1 else ""
                    title=vals[0] if vals else "Unknown"
                    # Prefer actual music/official results. Penalize live/covers/remixes
                    # because they make discovery less predictable and repeat heavily.
                    low=(title+" "+artist).lower()
                    if not any(x in low for x in ("live", "cover", "karaoke", "tutorial", "remix", "unofficial")):
                        out.append({"id":pid,"title":title,"artist":artist})
            mc=x.get("musicCardShelfRenderer")
            if mc:
                vid=(mc.get("onTap",{}).get("watchEndpoint",{}).get("videoId"))
                if not vid:
                    for b in mc.get("buttons",[]) or []:
                        vid=b.get("buttonRenderer",{}).get("navigationEndpoint",{}).get("watchEndpoint",{}).get("videoId")
                        if vid: break
                if vid:
                    runs=mc.get("title",{}).get("runs",[]) or []
                    subs=mc.get("subtitle",{}).get("runs",[]) or []
                    out.insert(0,{"id":vid,"title":"".join(v.get("text","") for v in runs),"artist":"".join(v.get("text","") for v in subs).split(" • ")[0]})
            for v in x.values(): walk(v)
    walk(data)
    uniq=[]; seen=set()
    for v in out:
        if v["id"] not in seen:
            seen.add(v["id"]); uniq.append(v)
    return uniq[:20]

def score(v,d,query):
    now=time.time()
    artist=v.get("artist","").lower()
    vid=v["id"]
    s=100
    s+=float(d["artists"].get(artist,0))*20
    s+=float(d["plays"].get(vid,0))*2
    s+=float(d["likes"].get(vid,0))*30
    s-=float(d["skips"].get(vid,0))*20
    s-=float(d["seeds"].get(vid,0))*8
    s-=float(d["banned"].count(vid))*1000
    # 20% exploration: a random bonus prevents converging on a single catalog row.
    s+=random.random()*25
    return s

def cmd_seed():
    query=sys.argv[2] if len(sys.argv)>2 else ""
    d=load()
    try: rs=search(query)
    except Exception as e:
        print(query, file=sys.stderr); return 1
    if not rs:
        return 1
    # Ranked choice, but keep variety: avoid the top seed if played in the recent history.
    scored=sorted(rs,key=lambda v:score(v,d,query),reverse=True)
    pool=scored[:max(3,min(8,len(scored)))]
    weights=[max(1,5-i) for i in range(len(pool))]
    seed=random.choices(pool,weights=weights,k=1)[0]
    d.setdefault("seeds",{})[seed["id"]]=d["seeds"].get(seed["id"],0)+1
    save(d)
    print(seed["id"])

def log_event(kind, vid, title="", artist=""):
    d=load(); kind=kind.lower()
    if kind=="play":
        d.setdefault("plays",{})[vid]=d["plays"].get(vid,0)+1
        if artist: d.setdefault("artists",{})[artist.lower()] = d["artists"].get(artist.lower(),0)+0.5
    elif kind=="skip":
        d.setdefault("skips",{})[vid]=d["skips"].get(vid,0)+1
    elif kind=="like":
        d.setdefault("likes",{})[vid]=d["likes"].get(vid,0)+1
    elif kind=="ban": d.setdefault("banned",[]).append(vid)
    save(d)
    os.makedirs(BASE,exist_ok=True)
    with open(HISTORY,"a",encoding="utf-8") as f:
        f.write(json.dumps({"ts":int(time.time()),"kind":kind,"id":vid,"title":title,"artist":artist},ensure_ascii=False)+"\n")

def main():
    if len(sys.argv)<2: print("usage: ytm_preferences.py <seed|log> ...",file=sys.stderr); return 2
    if sys.argv[1]=="seed": return cmd_seed()
    if sys.argv[1]=="log": log_event(sys.argv[2],sys.argv[3],*sys.argv[4:])
    if sys.argv[1]=="show": print(json.dumps(load(),ensure_ascii=False,indent=2))
    if sys.argv[1]=="reset":
        save({"artists":{},"seeds":{},"queries":{},"banned":[],"plays":{},"skips":{},"likes":{}})
    return 0

if __name__=="__main__": sys.exit(main())
