#!/bin/env python3

'''
This tool can convert ungrouped lrc stream to List[List[LrcNote]]
LrcNote is Tuple[int, str] (seconds, content)

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

def flatMap(transform, xs):
  res = []
  for ys in map(transform, xs):
    for y in ys: res.append(y)
  return res

data = list(flatMap(readLrc, iter(lambda: input("lrc>"), ".")) )
print(data)


def require(value, p, msg):
  if not p(value): raise ValueError(f"{msg}: {value}")

def zipWithNext(xs):
  require(xs, lambda it: len(it) > 2, "must >2")
  for i in range(1, len(xs)):
    yield (xs[i-1], xs[i])

def zipTakeWhile(predicate, xs):
  col = [xs[0]]
  for (a, b) in zipWithNext(xs):
    if not predicate(a, b):
      yield col
      col = []
    col.append(b)
  yield col #< even predicate matches

from sys import argv
TIME_SPAN  = 1.0 if len(argv) != 2 else float(argv[1])
print("== lyrics")
inSameLine = lambda a, b: abs(a[0] - b[0]) < TIME_SPAN
result = list(zipTakeWhile(inSameLine, data) )
print(dumpLrc(result))


from datetime import timedelta
from srt import Subtitle, compose
def intoSrt(lrc_lines):
  time = lambda line: map(lambda it: timedelta(seconds=it[0]), line)
  text = lambda line: map(lambda it: it[1], line)
  return [Subtitle(i+1, min(time(line)), max(time(line)), "".join(text(line))) for i, line in enumerate(lrc_lines)]

with open("a.srt", "w+") as srtf:
  srtf.write(compose(intoSrt(result)))
