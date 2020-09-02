import threading
import traceback
import queue
from sys import stderr

from tkinter import Tk, Toplevel

from traceback import extract_stack #codegen autoname

from platform import system as platformName #< for startFile
from subprocess import call as startSubProcess
def startFile(path:str):
  name = platformName()
  def run(prog): startSubProcess((prog, path))
  if name == "Darwin": run("open")
  elif name == "Windows":
    __import__("os").startfile(path)
  else: run("xdg-open") # POSIX

MSG_CALL_FROM_THR_MAIN = "call from main thread."
MSG_CALLED_TWICE = "called twice"
NOT_THREADSAFE = RuntimeError("call initLooper() first")
TCL_CMD_POLLER = "teek_init_threads_queue_poller"

class BackendEnum():
  def __init__(self, name:str, module_name:str):
    self.name=name;self.module_name=module_name
  def __eq__(self, other): return other.name == self.name
  def __hash__(self): return self.name.__hash__()
  def isAvaliable(self):
    try: __import__(self.module_name); return True
    except ImportError: return False
  def use(self):
    global guiBackend
    if self.isAvaliable(): guiBackend = self
    else: next(filter(BackendEnum.isAvaliable, Backend.fallbackOrder)).use()

class Backend:
  Tk = BackendEnum("tk", "tkinter")
  TTk = BackendEnum("ttk", "tkinter.ttk")
  Wx = BackendEnum("wx", "wx")
  GTK = BackendEnum("gtk", "gi")
  fallbackOrder = [GTK, Wx, TTk, Tk]
guiBackend = Backend.TTk

class SyntaxFmt:
  '''some language-sepcific syntax formatters'''
  @staticmethod
  def pyArg(params):
    '''arg1, arg2, kw1=kw1v, kw2=kw2v'''
    (args, kwargs) = params
    sb = []
    sb.extend(args)
    for (name, v) in kwargs.items(): sb.append("%s=%s" %(name, v) )
    return ", ".join(sb)
  @staticmethod
  def guiAutoExpr(x):
    from .tkgui import TkWin # never import previor than tkgui imports us
    def noargNew(t): return fmt.callNew(t, ([],{}))
    if isinstance(x, Toplevel): return noargNew(Toplevel)
    elif isinstance(x, TkWin): return noargNew(TkWin) # fallback workaround, behaves VERY ugly (spawn useless wins)
    return None
  argList = pyArg
  value = repr
  list = lambda xs: "[%s]" %", ".join(xs)
  assign = lambda name, x: "%s = %s" %(name, x)
  nameRef = lambda name: name   #v add checks for __self__ ?
  opRef = lambda op: op.__qualname__ if op.__qualname__.replace(".", "").isidentifier() else None #e.g. lambda, check not serious
  call = lambda name, params: "%s(%s)" %(name, SyntaxFmt.argList(params))
  callNew = lambda ty, params: "%s(%s)" %(ty.__qualname__, SyntaxFmt.argList(params))
  invoke = lambda x, op_name, params: "%s.%s(%s)" %(x, op_name, SyntaxFmt.argList(params))
  setAttr = lambda x, name, v: "%s.%s = %s" %(x, name, v)
  setItem = lambda x, key, v: "%s[%s] = %s" %(x, SyntaxFmt.value(key), v)
  tfNil = ("True", "False", "None")
  lineSep = "\n"
  autoExpr = lambda x: SyntaxFmt.guiAutoExpr(x)
  specialCaller = "createWidget"
  defaultNameMap = {}
fmt = SyntaxFmt

def indexOfLast(p, xs):
  idxPart = 0; idxXs = len(xs) -1
  for (i, x) in enumerate(reversed(xs)):
    if not p(x): idxPart = idxXs-i +1; break
  return idxPart

class Codegen:
  '''Python stmt/expression construction&execution result provider,
    so adding side-effects(generate code) besides values are possible.
    The code generator generally uses value-name substitution,
    to provide generated-file-wise argument, use [named] method.
    NOTE: non-flat syntax structures are NOT supported, the result is mainly post-order tree walk'''
  isEnabled = False
  useDebug = False
  def __init__(self):
    super().__init__()
    self._sb = []
    self._names = id_dict(); self._exprs = id_dict()
    self._autoNamed = id_set()
    self._constNames = Codegen._initConstNames()
  @staticmethod
  def _initConstNames():
    (t,f,nil) = fmt.tfNil
    return id_dict({True: t, False:f, None: nil})
  def clear(self):
    self._sb = []
    self._names.clear(); self._exprs.clear()
    self._autoNamed.clear()
    self._constNames = Codegen._initConstNames()
  def write(self, get_text):
    if not Codegen.isEnabled: return
    text = get_text()
    if Codegen.isEnabled: self._sb.append(text)
  def getCode(self):
    code = fmt.lineSep.join(self._sb)
    if Codegen.useDebug: print(code)
    return code

  @staticmethod
  def nextName(name:str):
    '''a, a1, a2, ...'''
    if name == "": return "_"
    if not name[-1].isnumeric(): return "%s1" %name
    else:
      idxNPart = indexOfLast(str.isnumeric, name)
      return "%s%d" %(name[:idxNPart], 1+int(name[idxNPart:]))
  def _allocName(self, name):
    qname = name # find, could be tailrec
    while qname in self._names.values(): qname = Codegen.nextName(qname)
    return qname
  def named(self, name, x, is_extern=False):
    '''this may give an value a name, if [x] is provided before, then [nextName] is used. see [nv]'''
    self._names[x] = self._allocName(name)
    if is_extern:
      assert name not in self._constNames, "extern duplicate: %s" %name
      self._constNames[x] = name
    return x
  def newName(self, name, x):
    '''give [x] a new name'''
    self.named(name, x)
    return self._names.get(x)

  def _nvUnwrap(self, x):
    if isinstance(x, list): return fmt.list([self.nv(it) for it in x])
    return None
  def nv(self, x):
    '''name a expression result, note [named] could not be used twice on the same value,
      or inconsistence nameRef (e.g. created@callNew foo, re-named to xxx later) will be wrote'''
    def nameRef():
      kst = self._constNames.get(x)
      if kst != None: return kst
      nam = self._names.get(x)
      if nam != None: nam = fmt.nameRef(nam)
      return nam or self._nvUnwrap(x) or fmt.value(x)
    expr = self._exprs.get(x)
    if expr == None:
      expr = fmt.autoExpr(x)
      if expr != None: self._autoNamed.add(x)
    if expr != None and expr != "+":
      name = self._names.get(x)
      if name == None and (x in self._autoNamed):
        name = self.newName("%s_1" %type(x).__name__.lower(), x)
      if name != None: self.write(lambda: fmt.assign(name, expr) )
      self._exprs[x] = "+"
    return nameRef()
  def _regResult(self, res, get_code):
    if not Codegen.isEnabled: return
    if res == None: self.write(get_code); return # python's default func result
    code = get_code()
    self._exprs[res] = code
    self._autoNamed.add(res)
  def _name(self, args, kwargs):
    '''name those actual param values'''
    namArgs = [self.nv(arg) for arg in args]
    namKwargs = {}
    for (key, x) in kwargs.items():
      if callable(x):
        qname = fmt.opRef(x)
        if qname != None: namKwargs[key] = qname
      else: namKwargs[key] = self.nv(x)
    return (namArgs, namKwargs)
  def defaultName(self, callee, x):
    return fmt.defaultNameMap.get(callee) or callee

  def call(self, op, *args, **kwargs):
    res = op(*args, **kwargs)
    self._regResult(res, lambda: fmt.call(op, self._name(args, kwargs)))
    return res
  def callNew(self, ctor, *args, **kwargs):
    insta = ctor(*args, **kwargs)
    self._regResult(insta, lambda: fmt.callNew(ctor, self._name(args, kwargs)))
    tb = extract_stack(limit=3) # determine whatif result is a GUI widget
    (caller, callee) = [it[2] for it in tb[:-1]] #drop this "call"'s frame, get func name(2)
    if caller == fmt.specialCaller:
      deftName = self.defaultName(callee, insta)
      if deftName != None: self.named(deftName, insta) # scope[value] may rewrote to new name
    return insta
  def invoke(self, x, op_name, *args, **kwargs):
    res = x.__getattribute__(op_name)(*args, **kwargs)
    self._regResult(res, lambda: fmt.invoke(self.nv(x), op_name, self._name(args, kwargs)))
    return res
  def setAttr(self, x, name, v):
    x.__setattr__(name, v)
    self.write(lambda: fmt.setAttr(self.nv(x), name, self.nv(v)) )
  def setItem(self, x, key, v):
    x[key] = v
    self.write(lambda: fmt.setItem(self.nv(x), key, self.nv(v)) )


class EventCallback:
  """An object that calls functions. Use [bind] / [__add__] or [run]"""
  def __init__(self):
    self._callbacks = []

  class CallbackBreak: pass
  callbackBreak = CallbackBreak()
  @staticmethod
  def stopChain(): raise callbackBreak

  def isIgnoredFrame(self, frame):
    '''Is a stack trace frame ignored by [bind]'''
    return False
  def bind(self, op, args=(), kwargs={}):
    """Schedule `callback(*args, **kwargs) to [run]."""
    stack = traceback.extract_stack()
    while stack and self.isIgnoredFrame(stack[-1]): del stack[-1]
    stack_info = "".join(traceback.format_list(stack))
    self._callbacks.append((op, args, kwargs, stack_info))
  def __add__(self, op):
    self.bind(op); return self

  def remove(self, op):
    """Undo a [bind] call. only [op] is used as its identity, args are ignored"""
    idx_callbacks = len(self._callbacks) -1 # start from 0
    for (i, cb) in enumerate(self._callbacks):
      if cb[0] == op:
        del self._callbacks[idx_callbacks-i]
        return

    raise ValueError("not bound: %r" %op)

  def run(self) -> bool:
    """Run the connected callbacks(ignore result) and print errors. If one callback requested [stopChain], return False"""
    for (op, args, kwargs, stack_info) in self._callbacks:
      try: op(*args, **kwargs)
      except EventCallback.CallbackBreak: return False
      except Exception:
        # it's important that this does NOT call sys.stderr.write directly
        # because sys.stderr is None when running in windows, None.write is error
        (trace, rest) = traceback.format_exc().split("\n", 1)
        print(trace, file=stderr)
        print(stack_info+rest, end="", file=stderr)
        break
    return True

class FutureResult:
  '''pending operation result, use [getValue] / [getValueOr] to wait'''
  def __init__(self):
    self._cond = threading.Event()
    self._value = None
    self._error = None

  def setValue(self, value):
    self._value = value
    self._cond.set()

  def setError(self, exc):
    self._error = exc
    self._cond.set()

  def getValueOr(self, on_error):
    self._cond.wait()
    if self._error != None: on_error(self._error)
    return self._value
  def getValue(self): return self.getValueOr(FutureResult.rethrow)
  def fold(self, done, fail):
    self._cond.wait()
    return done(self._value) if self._error == None else fail(self._error)
  @staticmethod
  def rethrow(ex): raise ex

class EventPoller:
  '''after-event loop operation dispatcher for Tk'''
  def __init__(self):
      assert threading.current_thread() is threading.main_thread()
      self._main_thread_ident = threading.get_ident() #< faster than threading.current_thread()
      self._init_looper_done = False
      self._call_queue = queue.Queue() # (func, args, kwargs, future)
      self.tk:Tk; self.on_quit:EventCallback
  def isThreadMain(self): return threading.get_ident() == self._main_thread_ident
  def initLooper(self, poll_interval_ms=(1_000//20) ):
      assert self.isThreadMain(), MSG_CALL_FROM_THR_MAIN
      assert not self._init_looper_done, MSG_CALLED_TWICE #< there is a race condition, but just ignore this

      timer_id = None
      def poller():
        nonlocal timer_id
        while True:
          try: item = self._call_queue.get(block=False)
          except queue.Empty: break

          (func, args, kwargs, future) = item
          try: value = func(*args, **kwargs)
          except Exception as ex: future.setError(ex)
          else: future.setValue(value)

        timer_id = self.tk.tk.call("after", poll_interval_ms, TCL_CMD_POLLER)
      self.tk.tk.createcommand(TCL_CMD_POLLER, poller)

      def quit_cancel_poller():
        if timer_id != None: self.tk.after_cancel(timer_id)

      self.on_quit += quit_cancel_poller

      poller()
      self._init_looper_done = True

  def callThreadSafe(self, op, args, kwargs) -> FutureResult:
    if self.isThreadMain():
      return op(*args, **kwargs)

    if not self._init_looper_done: raise NOT_THREADSAFE

    future = FutureResult()
    self._call_queue.put((op, args, kwargs, future))
    return future


# boilerplates
class id_dict(dict):
  '''try to store objects, use its identity to force store unhashable types'''
  def get(self, key): return super().get(id(key))
  def __getitem__(self, key): return super().__getitem__(id(key))
  def __setitem__(self, key, value): return super().__setitem__(id(key), value)
  def __delitem__(self, key): return super().__delitem__(id(key))
  def __contains__(self, key): return super().__contains__(id(key))
class id_set(set):
  '''same as [id_dict]'''
  def add(self, value): super().add(id(value))
  def remove(self, value): super().remove(id(value))
  def __contains__(self, value): return super().__contains__(id(value))

guiCodegen = Codegen()
