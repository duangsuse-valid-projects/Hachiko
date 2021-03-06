from argparse import ArgumentParser, FileType
from json import loads, dumps


from .tkgui_utils import startFile, Backend
from .tkgui_utils import guiCodegen as c
Backend.TTk.use()

from .tkgui import TkGUI, TkWin, MenuItem, TreeWidget, nop, Timeout, callThreadSafe, thunkifySync, delay, runAsync, rescueWidgetOption
from tkinter import Menu

import threading, time, requests
import os

app = ArgumentParser(prog="hachi-groups", description="GUI tool for recording lyric sentences with hachi")
app.add_argument("music", type=FileType("r"), help="music BGM to play")
app.add_argument("-seek-minus", type=float, default=3.0, help="back-seek before playing the sentence")
app.add_argument("-mix-multi", action="store_true", default=False, help="give multi-track mix")
app.add_argument("-o", type=str, default="mix.mid", help="mixed output file")
app.add_argument("-replay", type=FileType("r"), default=None, help="MIDI File to replay")
app.add_argument("-import", type=str, default=None, help="import a sentence list")

#GUI: ($lyric @ $n s .Rec-Edit .Play)[] (input-lyric @ input-n s .Add .Remove_Last) (input-JSON .Mix .Delete .Export) (-) ($music) (slider-volume)
rescueWidgetOption["relief"] = lambda _: None

class GUI(TkGUI):
  def up(self):
    self.a.set("wtf")
    self.ui.removeChild(self.ui.lastChild)
    GUI.ThreadDemo().run("Thread Demo")
  def pr(self):
    print(self.c.get())
    self.ui.removeChild(self.ui.childs[5])
  def layout(self):
    _ = self.underscore
    c.setAttr(self, "a", _.var(str, "some"))
    c.setAttr(self, "b", _.var(bool))
    c.setAttr(self, "c", _.var(int))
    def addChild(): self.ui.appendChild(_.text("hhh"))
    return _.verticalLayout(
      _.button("Yes", self.quit),
      _.text(self.a),
      _.button("Change", self.up),
      _.horizontalLayout(_.text("ex"), _.text("wtf"), _.button("emmm",addChild), _.text("aa")),
      _.input("hel"),
      _.separator(),
      _.withScroll(_.vert, _.by("ta", _.textarea("wtf"))),
      _.by("ah", _.text("ah")),
      _.checkBox("Some", self.b),
      _.horizontalLayout(_.radioButton("Wtf", self.c, 1, self.pr), _.radioButton("emm", self.c, 2, self.pr)),
      _.horizontalLayout(
        _.by("sbar", _.scrollBar(_.vert)),
        _.verticalLayout(
          _.by("lbox", _.listBox(("1 2 3  apple juicy lamb clamp banana  "*20).split("  "))),
          _.by("hsbar", _.scrollBar(_.hor))
        )
      ),
      _.withScroll(_.both, _.by("box", _.listBox(("1 2 3  apple juicy lamb clamp banana  "*20).split("  ")))),
      _.comboBox(self.a, "hello cruel world".split(" ")),
      _.spinBox(range(0, 100+1, 10)),
      _.slider(range(0, 100+1, 2), orient=_.hor),
      _.button("hello", self.run1),
      _.button("split", self.run2),
      _.menuButton("kind", _.menu(MenuItem.CheckBox("wtf", self.b), MenuItem.RadioButton("emm", self.c, 9)), relief=_.raised),
      _.labeledBox("emmm", _.button("Dangerous", self.run3))
    )
  def run1(self): GUI.Layout1().run("Hello")
  def run2(self): a=GUI.SplitWin(); a.runCode(a.getCode()) #.run("Split")
  def run3(self): print(self.ta.marker["insert"])
  def setup(self):
    _ = self.underscore
    _.bindYScrollBar(self.lbox, self.sbar)
    _.bindXScrollBar(self.lbox, self.hsbar)
    themes = self.listThemes()
    themez = iter(themes)
    self.ah["text"] = ",".join(themes)
    def nextTheme(event):
      nonlocal themez
      try: self.theme = next(themez)
      except StopIteration:
        themez = iter(themes)
    self.ah.bind(_.Events.click, nextTheme)
    self.ah.bind(_.Events.mouseR, _.makeMenuPopup(_.menu(*[MenuItem.named(it, nop) for it in "Cut Copy Paste Reload".split(" ")], MenuItem.sep, MenuItem.named("Rename", nop))))
    self.initLooper()

  class Layout1(TkWin):
    def layout(self):
      _ = self.underscore
      return _.verticalLayout(
        _.text("Hello world"),
        _.by("can", _.canvas((250, 300)))
      )
    def setup(self):
      menubar = self.menu(self.tk,
        MenuItem.named("New", nop),
        MenuItem.named("Open", lambda: GUI.DoNothing().run("x")),
        MenuItem.SubMenu("Help", [MenuItem.named("Index...", nop), MenuItem.sep, MenuItem.named("About", nop)])
      )
      self.setMenu(menubar)
      self.setSizeBounds((200,100))
      self.addSizeGrip()
      self.can["bg"] = "blue"
      coord = (10, 50, 240, 210)
      self.can.create_arc(coord, start=0, extent=150, fill="red")
  class SplitWin(TkWin):
    def layout(self):
      _ = self.underscore
      return _.withFill(_.splitter(_.hor,
        _.text("left pane"),
        _.splitter(_.vert,
          _.text("top pane"),
          _.text("bottom pane")
        )
      ))
  class DoNothing(TkWin):
    def __init__(self):
      super().__init__()
      self.nodes = dict()
      self.ftv:TreeWidget
    def layout(self):
      _ = self.underscore
      return _.withFill(_.tabWidget(
        ("Tab 1", _.text("a")),
        ("Tab 2", _.verticalLayout(_.text("Lets dive into the world of computers"))),
        ("TabTree", _.by("tv", _.treeWidget())),
        ("File Man", _.by("ftv", _.treeWidget()))
      ))
    def setup(self):
      self.tv.makeTree(["Name", "Desc"], [
        "GeeksforGeeks",
        ("Computer Science", [
          ["Algorithm", "too hard"],
          ["Data structure", "just right"]
        ]),
        ("GATE papers", [
          "2018", "2019"
        ]),
        ("Programming Languages", [
          "Python", "Java"
        ])
      ])
      self.tv.item("GATE papers").moveTo("GeeksforGeeks")
      abspath = os.path.abspath(".")
      #self.ftv.makeTree(["Name"], [(abspath, ["a"])])
      self.ftv.heading('#0', text='Project tree', anchor='w')
      self.insertNode(self.ftv.rootItem, abspath, abspath)
      self.ftv.bind(TreeWidget.onOpen.name, self.openNode)
    def insertNode(self, parent, text, abspath):
      node = parent.addChild(text)
      if os.path.isdir(abspath):
        self.nodes[node] = abspath
        node.addChild(None)
    def openNode(self, event):
      node = self.ftv.focusItem
      abspath = self.nodes.pop(node, None)
      if abspath:
        print(abspath)
        node.removeChilds()
        for p in os.listdir(abspath):
          self.insertNode(node, p, os.path.join(abspath, p))
      else: startFile(node.id)
  class ThreadDemo(TkWin):
    def __init__(self):
      super().__init__()
      self.ta = None
      _ = self.underscore
      self.active = _.var(str)
      self.confirmed = _.var(str)
    def layout(self):
      _ = self.underscore
      return _.verticalLayout(
        _.by("ta", _.textarea()),
        _.createLayout(_.hor, 0, _.text("Total active cases: ~"), _.text(self.active)),
        _.createLayout(_.vert, 0, _.text("Total confirmed cases:"), _.text(self.confirmed)),
        _.button("Refresh", self.on_refresh)
      )
    url = "https://api.covid19india.org/data.json"
    def on_refresh(self):
      runAsync(thunkifySync(requests.get, self.url), self.on_refreshed)
      runAsync(delay(1000), lambda ms: self.ta.insert("end", "233"))

    def on_refreshed(self, page):
      data = loads(page.text)
      #print(data)
      self.active.set(data["statewise"][0]["active"])
      self.confirmed.set(data["statewise"][0]["confirmed"])
      self.btn_refresh["text"] = "Data refreshed"
    def setup(self):
      self.setSizeBounds((220, 70))
      threading.Thread(target=self.thread_target).start()
    def thread_target(self):
      callThreadSafe(lambda: self.setSize(self.size, (0,0)))
      def addText(text): callThreadSafe(lambda: self.ta.insert("end", text))
      addText('doing things...\n')
      time.sleep(1)
      addText('doing more things...\n')
      time.sleep(2)
      addText('done')

from sys import argv
from .tkgui_utils import Codegen
def main(args = argv[1:]):
  cfg = app.parse_args(args)
  gui = GUI()
  #gui.run("Application")
  Codegen.useDebug = True
  gui.runCode(gui.getCode(False), GUI=gui, TkGUI=gui)
