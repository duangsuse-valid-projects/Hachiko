#!/bin/env python3
# -*- coding: utf-8 -*-

from ctypes import CDLL, CFUNCTYPE
from ctypes.util import find_library

from sys import platform as sys_platform
from os import name as os_name

def findLibrary(name, lib_names) -> str:
  try:
    return next(filter(lambda it: it != None, map(find_library, lib_names))) or ""
  except StopIteration:
    raise ImportError(f"Couldn't find the {name} library")

def createLibrary(path, mode = 1):
  lib = CDLL(path)
  def cfunc(name, t_result, *args):
    t_args = tuple(arg[1] for arg in args)
    extras = tuple((mode, arg[0]) for arg in args)
    return CFUNCTYPE(t_result, *t_args)((name, lib), extras)
  return cfunc

def platform(opts = {"linux": "linux", "windows": "windows", "macos": "macos"}):
  for (k, v) in opts.items():
    if sys_platform.lower().startswith(k): return v
  return os_name


def require(value, p, message):
  if not p(value): raise ValueError(f"{message}: {value}")

isNonnegative = lambda it: it >= 0
def isInbounds(start, stop):
  return lambda it: it in range(start, stop)

def hasIndex(i):
  return lambda xs: i in range(0, len(xs))

def flatMap(f, xs):
  for ys in map(f, xs):
    for y in ys: yield y

global cdecls #v define a subset of C Header
if __name__ == "__main__":
  import pyparsing as pas
  LBRACE, RBRACE, SEMI = map(pas.Suppress, "();")
  identifier = pas.Word(pas.alphas, pas.alphanums + "_")
  typename = pas.Word(identifier.bodyCharsOrig + "*")
  cdecl_arg = typename("type") + identifier("name")
  cdecl = typename("t_result") + identifier("fname") +LBRACE+ pas.Optional(pas.delimitedList(cdecl_arg)) +RBRACE+SEMI
  cdecls = pas.ZeroOrMore(pas.Group(cdecl))

ctype = {
  "void": "None", "void*": "c_void_p", "char*": "c_char_p",
  "int": "c_int", "double": "c_double"
}.__getitem__
def post_cdecl(m):
  """t_result fname(type name, ...args);"""
  t_result, fname = m[0:2]
  if len(m) == 2: return (fname, ctype(t_result), [])
  args = [(m[i+1], ctype(m[i])) for i in range(2, len(m), 2)]
  return (fname, ctype(t_result), args)

from sys import argv

def codegen(path_dst, path_header, name, lib_names):
  output = open(path_dst, "w+", encoding="utf-8")
  def line(text = ""): output.write(text); output.write("\n")

  def preheader():
    line("# -*- coding: utf-8 -*-")
    line("from funutils import findLibrary, createLibrary")
    line("# DO NOT EDIT"); line(f"#This file was generated by {' '.join(argv)}")
  def libdefs():
    line(f"lib_names = {repr(lib_names)}")
    line(f"lib_path = findLibrary({repr(name)}, lib_names)")
    line(f"cfunc = createLibrary(lib_path)")
  def cimport(decls):
    imports = set(filter(lambda it: it.startswith("c_"), flatMap(lambda it: [it[1]] + [a[1] for a in it[2]], decls)))
    imports_code = f"from ctypes import {', '.join(imports)}"
    print(imports_code); line(imports_code)
  def cdefs(decls):
    for decl in decls:
      rest = "" if len(decl[2]) == 0 else ",\n  " + ", ".join([f"({repr(name)}, {ty})" for (name, ty) in decl[2]])
      line(f"{decl[0]} = cfunc({repr(decl[0])}, {decl[1]}{rest})")

  preheader()
  line()
  libdefs()
  line()
  with open(path_header, "r") as header:
    decls = list(map(post_cdecl, cdecls.parseFile(header)))
    cimport(decls)
    line()
    cdefs(decls)
  output.close()

def main(argv):
  if len(argv) < 4:
    print(f"Usage: {argv[0]} header name lib_names")
    return
  header, name = argv[1:3]
  codegen(f"{name}.py", header, name, argv[3:])

if __name__ == '__main__': main(argv)
