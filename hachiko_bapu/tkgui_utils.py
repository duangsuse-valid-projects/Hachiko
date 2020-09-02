import threading
import traceback
import queue
from sys import stderr

from tkinter import Tk

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
  argList = pyArg
  value = repr
  assign = lambda name, x: "%s = %s" %(name, x)
  nameRef = lambda name: name
  call = lambda name, params: "%s(%s)" %(name, SyntaxFmt.argList(params))
  callNew = lambda qname, params: "%s(%s)" %(qname, SyntaxFmt.argList(params))
  invoke = lambda recv, op_name, params: "%s.%s(%s)" %(recv, op_name, SyntaxFmt.argList(params))
  setAttr = lambda x, name, v: "%s.%s = %s" %(x, name, v)
  setItem = lambda x, key, v: "%s[%s] = %s" %(x, SyntaxFmt.value(key), v)
  forEach = lambda x: ("for it in %s: " %(x), "")
  forEachIndexed = lambda x: ("for (i, it) in %s: " %(x), "")
  cond = lambda x, a, b: "(%s if %s else %s)" %(a, x, b)
  tfNil = ("True", "False", "None")
fmt = SyntaxFmt

def indexOfLast(p, xs):
  idxPart = 0; idxXs = len(xs) -1
  for (i, x) in enumerate(reversed(xs)):
    if not p(x): idxPart = idxXs-i +1; break
  return idxPart

class id_dict(dict):
  '''try to store objects, if not hashable, use its id to force store (but added as non-enumeratable)'''
  def __init__(self, initial:dict = {}):
    super().__init__()
    self._ids = {}
    for (k, v) in initial.items(): self[k] = v
  def clear(self): super().clear(); self._ids.clear()
  def get(self, key):
    try: return super().get(key)
    except TypeError: return self._ids.get(id(key))
  def __getitem__(self, key):
    try: return super().__getitem__(key)
    except TypeError: return self._ids[id(key)]
  def __setitem__(self, key, value):
    try: return super().__setitem__(key, value)
    except TypeError: self._ids[id(key)] = value
  def __delitem__(self, key):
    try: return super().__delitem__(key)
    except TypeError: del self._ids[id(key)]

class Codegen:
  '''Python stmt/expression construction&execution result provider,
    so adding side-effects(generate code) besides values are possible.
    The code generator generally uses value-name substitution,
    to provide generated-file-wise argument, use [named] method.
    NOTE: non-flat syntax structures are NOT supported'''
  isEnabled = False
  def __init__(self):
    super().__init__()
    self._sb = []
    self._names = id_dict()
    (t,f,nil) = fmt.tfNil
    self._constName = id_dict({True: t, False:f, None: nil})
  def write(self, text):
    print(text)
    if Codegen.isEnabled: self._sb.append(text)
  def getCode(self): return "".join(self._sb)

  @staticmethod
  def nextName(name:str):
    '''a, a1, a2, ...'''
    if name == "": return "_"
    if not name[-1].isnumeric(): return "%s1" %name
    else:
      idxNPart = indexOfLast(str.isnumeric, name)
      return "%s%d" %(name[:idxNPart], 1+int(name[idxNPart:]))
  def nv(self, x):
    '''name a expression result'''
    def nvList():
      if isinstance(x, list): return [self.nv(it) for it in x]
      return None
    return self._constName.get(x) or self._names.get(x) or nvList()
  def nvr(self, x): return self.nv(x) or fmt.value(x)
  def _regResult(self, res, get_code):
    if not Codegen.isEnabled: return
    code = get_code()
    self._names[res] = code
  def _name(self, args, kwargs):
    '''name those actual param values'''
    namArgs = [self.nvr(arg) for arg in args]
    namKwargs = {}
    for (key, x) in kwargs.items():
      got = self.nv(x)
      if got != None: namKwargs[key] = got
      else:
        if callable(x): continue
        namKwargs[key] = fmt.value(x)
    return (namArgs, namKwargs)

  def named(self, name, x, is_extern=False):
    '''this may give an value a name, if [x] is provided before, then [nextName] is used'''
    if not is_extern: print(fmt.assign(name, self.nv(x) or fmt.value(x)))
    self._names[x] = name if name not in self._names.values() else Codegen.nextName(name)
    return x
  def call(self, op, *args, **kwargs):
    res = op(*args, **kwargs)
    self._regResult(res, lambda: fmt.call(op, self._name(args, kwargs)))
    return res
  def callNew(self, ctor, *args, **kwargs):
    qname = ctor.__qualname__
    insta = ctor(*args, **kwargs)
    self._regResult(insta, lambda: fmt.callNew(qname, self._name(args, kwargs)))
    tb = extract_stack(limit=3) # determine whatif result is a GUI widget
    (caller, callee) = [it[2] for it in tb[:-1]] #drop this "call"'s frame, get func name(2)
    if caller == "createWidget":
      self.named(callee, insta, is_extern=True) # scope[value] may rewrote to new name
    return insta
  def invoke(self, x, op_name, *args, **kwargs):
    res = x.__getattribute__(op_name)(*args, **kwargs)
    self._regResult(res, lambda: fmt.invoke(self.nv(x), op_name, self._name(args, kwargs)))
    return res
  def setAttr(self, x, name, v):
    x.__setattr__(name, v)
    self.write(fmt.setAttr(self.nv(x), name, self.nvr(v)) )
  def setItem(self, x, key, v):
    x[key] = v
    self.write(fmt.setItem(self.nv(x), key, self.nvr(v)) )
  def forEach(self, x, proc):
    for it in x: proc(self.named("it", it))
  def forEachIndexed(self, x, proc):
    for (i, it) in enumerate(x): proc(self.named("i", i), self.named("it", it))
  def cond(self, x, a, b):
    res = a if x else b
    self.write(fmt.cond(self.nvr(x), self.nvr(a), self.nvr(b)))
    return res

guiCodegen = Codegen()

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
