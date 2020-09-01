import threading
import traceback
import queue
from sys import stderr

from tkinter import Tk

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

useTheme = True
def dontUseTheme():
  global useTheme; useTheme = False

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

  def callThreadSafe(self, op, args, kwargs):
    if self.isThreadMain():
      return op(*args, **kwargs)

    if not self._init_looper_done: raise NOT_THREADSAFE

    future = FutureResult()
    self._call_queue.put((op, args, kwargs, future))
    return future
