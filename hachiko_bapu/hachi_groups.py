from argparse import ArgumentParser, FileType
from json import loads, dumps

from tkinter import Menu
from .tkgui import TkGUI, TkWin, MenuItem, nop

app = ArgumentParser(prog="hachi-groups", description="GUI tool for recording lyric sentences with hachi")
app.add_argument("music", type=FileType("r"), help="music BGM to play")
app.add_argument("-seek-minus", type=float, default=3.0, help="back-seek before playing the sentence")
app.add_argument("-mix-multi", action="store_true", default=False, help="give multi-track mix")
app.add_argument("-o", type=str, default="mix.mid", help="mixed output file")
app.add_argument("-replay", type=FileType("r"), default=None, help="MIDI File to replay")
app.add_argument("-import", type=str, default=None, help="import a sentence list")

#GUI: ($lyric @ $n s .Rec-Edit .Play)[] (input-lyric @ input-n s .Add .Remove_Last) (input-JSON .Mix .Delete .Export) (-) ($music) (slider-volume)

class GUI(TkGUI):
  def __init__(self):
    super().__init__()
    var = self.var
    self.a, self.b, self.c = var(str, "some"), var(bool), var(int)
  def up(self):
    self.a.set("wtf")
    self.ui.removeChild(self.ui.lastChild)
  def layout(self):
    _ = self.underscore
    def pr():
      print(self.c.get())
      self.ui.removeChild(self.ui.childs[5])
    def addChild(): self.ui.appendChild(_.text("hhh"))
    return _.verticalLayout(
      _.button("Yes", print),
      _.text(self.a),
      _.button("Change", self.up),
      _.horizontalLayout(_.text("ex"), _.text("wtf"), _.button("emmm",addChild), _.text("aa")),
      _.input("hel"),
      _.separator("Your Name"),
      _.textarea("wtf"),
      _.text("ah"),
      _.checkBox("Some", self.b),
      _.horizontalLayout(_.radioButton("Wtf", self.c, 1, pr), _.radioButton("emm", self.c, 2, pr)),
      _.horizontalLayout(
        _.by("sbar", _.scrollBar(_.vert)),
        _.verticalLayout(
          _.by("lbox", _.listBox(("1 2 3  apple juicy lamb clamp banana  "*20).split("  "))),
          _.by("hsbar", _.scrollBar(_.hor))
        )
      ),
      _.spinBox(range(0, 10+1)),
      _.slider(range(0, 100+1, 2), orient=_.hor),
      _.button("hello", lambda: GUI.Layout1().run("Hello")),
      _.button("split", lambda: GUI.SplitWin().run("Split")),
      _.menuButton("kind", _.menu(MenuItem.CheckBox("wtf", self.b), MenuItem.RadioButton("emm", self.c, 9)), relief=_.raised),
      _.labeledBox("emmm", _.button("Dangerous", lambda: print("233")))
    )
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
      self.setSize((200,100))
      self.can["bg"] = "blue"
      coord = (10, 50, 240, 210)
      self.can.create_arc(coord, start=0, extent=150, fill="red")
  class SplitWin(TkWin):
    def layout(self):
      _ = self.underscore
      return _.fill(_.splitter(_.hor,
        _.text("left pane"),
        _.splitter(_.vert,
          _.text("top pane"),
          _.text("bottom pane")
        )
      ))
  class DoNothing(TkWin):
    def layout(self):
      return self.button("Do nothing button", nop)
  def setup(self):
    self.bindYScrollBar(self.lbox, self.sbar)
    self.bindXScrollBar(self.lbox, self.hsbar)

from sys import argv
def main(args = argv[1:]):
  cfg = app.parse_args(args)
  gui = GUI()
  gui.run("Record Groups")
