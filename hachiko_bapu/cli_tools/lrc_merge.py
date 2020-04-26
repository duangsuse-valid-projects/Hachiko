#!/bin/env python3
# -*- coding: utf-8 -*-

'''
This tool can convert ungrouped lrc stream to List[List[LrcNote]]
LrcNote is Tuple[int, str] (seconds, content)
...wait, it's currently Subtitle(no, start, end, content)

Bad model: Lrc / LrcLines / Srt
read: str -> Lrc; dump: LrcLines -> str;
into: LrcLines -> ...
'''

from datetime import timedelta
from srt import Subtitle, compose
from srt import parse as fromSrt

from os import linesep

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

def map2D(f, xss):
  ''' map [[a]] with function f '''
  return map(lambda xs: [f(x) for x in xs], xss)

def cfgOrDefault(value, f, x):
  return value if value != None else f(x)


from re import compile
PAT_LRC_ENTRY = compile(r"[\[<](\d{2}):(\d{2}).(\d{2})[>\]] ?([^<\n]*)")

sepDeft = lambda line: ("" if all(map(lambda w: len(w) == 1, line)) else " ")

def readLrc(text):
  def readEntry(g): return (int(g[0])*60 + int(g[1]) + int(g[2]) / 100, g[3]) # [mm:ss.xx] content
  return [readEntry(e) for e in PAT_LRC_ENTRY.findall(text)]

def dumpLrc(lrc_lines, sep = None, surr1 = "[]", surr2 = "<>"):
  def header(t, surr): return "%s%02i:%02i.%02i%s" %(surr[0], t/60, t%60, t%1.0 * 100, surr[1])
  def formatLine(line):
    (t_fst, s_fst) = line[0]
    fmtFst = header(t_fst, surr1)+s_fst
    sep1 = cfgOrDefault(sep, sepDeft, map(lambda note: note[1], line))
    return fmtFst +sep1+ sep1.join([header(t, surr2) + s for (t, s) in line[1:]])
  return linesep.join(map(formatLine, lrc_lines))


def fromLrc(text, min_len):
  td = lambda t: timedelta(seconds=t)
  return [Subtitle(i+1, td(t), td(t+min_len), s) for i, (t, s) in enumerate(readLrc(text))]

def intoLrc(lines, sep=None): #v use join folding in dumpLrc
  return dumpLrc(map2D(lambda srt: (srt.start.total_seconds(), srt.content), lines), sep)

def intoSrt(srts, sep=None):
  def newContent(line):
    words = [srt.content for srt in line]
    return cfgOrDefault(sep, sepDeft, words).join(words)
  time = lambda it: it.start
  return [Subtitle(i+1, min(line, key=time).start, max(line, key=time).end, newContent(line)) for (i, line) in enumerate(srts)]

def readLines(name):
  print(f"input {name}, terminated by '.'")
  return iter(lambda: input(f"{name}>"), ".")

from sys import argv
def main(args = argv[1:]):
  from argparse import ArgumentParser
  app = ArgumentParser("lrc_merge",
    description="merge simple timeline LRC into line-splited LRC",
    epilog="if the result is truncated, try to split your input in lines")
  app.add_argument("-dist", type=float, default=0.8, help="max distance for words in same sentence")
  app.add_argument("-min-len", type=float, default=0.0, help="min duration for last word in sentence (LRC only)")
  app.add_argument("-o", type=str, default="a.srt", help="ouput SRT file")
  app.add_argument("-sep", type=str, default=None, help="word seprator (or decided automatically from sentence)")
  app.add_argument("file", type=str, help="input SRT file (or 'lrc' and input from stdin)")

  cfg = app.parse_args(args)
  use_lrc = cfg.file == "lrc"
  inSameLine = lambda a, b: abs((a.start if use_lrc else a.end) - b.start).total_seconds() < cfg.dist

  #v regex findall has input size limitations...
  data = list(flatMap(lambda t: fromLrc(t, cfg.min_len), readLines("lrc")) if use_lrc else fromSrt(open(cfg.file).read()))
  print(" ".join([f"{srt.start.total_seconds()};{srt.content}" for srt in data]))

  print("== lyrics")
  result = list(zipTakeWhile(inSameLine, data) )
  print(intoLrc(result, cfg.sep))

  with open(cfg.o, "w+") as srtf:
    srtf.write(compose(intoSrt(result, cfg.sep)))

if __name__ == "__main__": main()
