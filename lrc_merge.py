#!/bin/env python3

from datetime import timedelta
from srt import Subtitle, parse, compose

def require(value, p, msg = "bad"):
  if not p(value): raise ValueError(f"{msg}: {value}")

def zipWithNext(xs):
  require(xs, lambda it: len(it) > 2, "must >2")
  for i in range(1, len(xs)):
    yield (xs[i-1], xs[i])

def zipTakeWhile(predicate, xs):
  require(xs, lambda it: len(it) > 1)
  col = [xs[0]]
  for (a, b) in zipWithNext(xs):
    if not predicate(a, b):
      yield col
      col = []
    col.append(b)
  yield col #< even predicate matches

def flatMap(transform, xs):
  res = []
  for ys in map(transform, xs):
    for y in ys: res.append(y)
  return res

def liftMap2D(f, xss):
  return map(lambda xs: [f(x) for x in xs], xss)

'''
This tool can convert ungrouped lrc stream to List[List[LrcNote]]
LrcNote is Tuple[int, str] (seconds, content)
...wait, it's currently Subtitle(no, start, end, content)

Bad model: Lrc / LrcLines / Srt
read: str -> Lrc; dump: LrcLines -> str;
into: LrcLines -> ...
'''

from re import compile
PAT_LRC_ENTRY = compile(r"[\[<](\d{2}):(\d{2}).(\d{2})[>\]] ?([^<\n]*)")

def readLrc(text):
  def readEntry(g): return (int(g[0])*60 + int(g[1]) + int(g[2]) / 100, g[3]) # [mm:ss.xx] content
  return [readEntry(e) for e in PAT_LRC_ENTRY.findall(text)]

def dumpLrc(lrc_lines):
  def header(t, surr="[]"): return "%s%02i:%02i.%02i%s" %(surr[0], t/60, t%60, t%1.0 * 100, surr[1])
  return "\n".join([header(lrcs[0][0]) + lrcs[0][1] + "".join([header(t, "<>") + s for (t, s) in lrcs[1:]]) for lrcs in lrc_lines])

def fromLrc(text, min_len):
  td = lambda t: timedelta(seconds=t)
  return [Subtitle(i+1, td(t), td(t+min_len), s) for i, (t, s) in enumerate(readLrc(text))]

def intoLrc(lines):
  return dumpLrc(liftMap2D(lambda srt: (srt.start.total_seconds(), srt.content), lines) )

def intoSrt(srts):
  time = lambda it: it.start
  text = lambda it: it.content
  return [Subtitle(i+1, min(line, key=time).start, max(line, key=time).end, "".join(map(text, line))) for i, line in enumerate(srts)]

def readLines(name):
  print(f"input {name}, terminated by '.'")
  return iter(lambda: input(f"{name}>"), ".")

if __name__ == "__main__":
  from argparse import ArgumentParser
  app = ArgumentParser("lrc_merge",
    description="merge simple timeline LRC into line-splited LRC",
    epilog="if the result is truncated, try to split your input in lines")
  app.add_argument("-dist", type=float, default=0.8, help="max distance for words in same sentence")
  app.add_argument("-min-len", type=float, default=0.0, help="min duration for last word in sentence (LRC only)")
  app.add_argument("-o", type=str, default="a.srt", help="ouput SRT file")
  app.add_argument("file", type=str, help="input SRT file (or 'lrc' and input from stdin)")

  cfg = app.parse_args()
  use_lrc = cfg.file == "lrc"
  inSameLine = lambda a, b: abs((a.start if use_lrc else a.end) - b.start).total_seconds() < cfg.dist

  data = list(flatMap(lambda t: fromLrc(t, cfg.min_len), readLines("lrc")) if use_lrc else parse(open(cfg.file).read()))
  print(" ".join([f"{srt.start.total_seconds()};{srt.content}" for srt in data]))

  print("== lyrics")
  result = list(zipTakeWhile(inSameLine, data) )
  print(intoLrc(result))

  with open(cfg.o, "w+") as srtf:
    srtf.write(compose(intoSrt(result)))
