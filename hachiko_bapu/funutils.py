#!/bin/env python3
# -*- coding: utf-8 -*-

from ctypes import CDLL, CFUNCTYPE
from ctypes.util import find_library

from sys import platform as sys_platform
from os.path import isfile, abspath
from itertools import chain

def require(value, p, message):
  if not p(value): raise ValueError(f"{message}: {value}")

isNotNone = lambda it: it != None
isNonnegative = lambda it: it >= 0
def isInbounds(start, stop):
  return lambda it: it in range(start, stop)

def hasIndex(i):
  return lambda xs: i in range(0, len(xs))

def flatMap(f, xs):
  for ys in map(f, xs):
    for y in ys: yield y

def takePipeIf(p, transform, value):
  res = transform(value)
  return res if p(res) else value

def findLibrary(name, lib_names, solver=lambda name: [f"./{name}.dll"]) -> str:
  paths = filter(isNotNone, map(find_library, lib_names))
  for dlls in map(solver, lib_names):
    paths = chain(paths, filter(isfile, dlls))

  path = next(paths, None) #< appended dll scan
  if path == None: raise ImportError(f"couldn't find the {name} library")
  else: return takePipeIf(isfile, abspath, str(path)) #< only if found file, not libname in PATH

def createLibrary(path, mode = 1):
  lib = CDLL(path)
  def cfunc(name, t_result, *args):
    t_args = tuple(arg[1] for arg in args)
    extras = tuple((mode, arg[0]) for arg in args)
    return CFUNCTYPE(t_result, *t_args)((name, lib), extras)
  return cfunc

def platform(opts = {"linux": ["linux"], "windows": ["win", "cygwin"], "macos": ["darwin"]}):
  for (v, ks) in opts.items():
    for k in ks:
      if sys_platform.lower().startswith(k): return v
  raise ValueError(f"unsupported platform: {sys_platform}")


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
from os.path import isfile

def isInsideModule(): return isfile("__init__.py")

def codegen(path_dst, path_header, name, lib_names):
  output = open(path_dst, "w+", encoding="utf-8")
  def line(text = ""): output.write(text); output.write("\n")

  def preheader():
    pkg_path = ".funutils" if isInsideModule() else "funutils"
    line("# -*- coding: utf-8 -*-")
    line(f"from {pkg_path} import findLibrary, createLibrary")
    line("# DO NOT EDIT"); line(f"#This file was generated by {' '.join(argv)}")
  def libdefs():
    line(f"lib_names = {repr(lib_names)}")
    line(f"lib_path = findLibrary({repr(name)}, lib_names)")
    line(f"cfunc = createLibrary(lib_path)")
  def cimport(decls):
    type_refs = flatMap(lambda it: [it[1]] + [arg[1] for arg in it[2]], decls)
    imports = set(filter(lambda it: it.startswith("c_"), type_refs))
    imports_code = f"from ctypes import {', '.join(sorted(imports))}"
    line(imports_code); print(imports_code)
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

def main(argv = argv):
  if len(argv) < 4:
    print(f"Usage: {argv[0]} header name lib_names")
    return
  header, name = argv[1:3]
  codegen(f"{name}.py", header, name, argv[3:])

if __name__ == '__main__': main()
