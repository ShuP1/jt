from __future__ import annotations

from rich.highlighter import ReprHighlighter
from rich.syntax import Syntax
from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Tree, TreeNode
from textual.events import Resize
from collections import deque
import json

class JSONDocument(Static):
    def load(self, text: str) -> bool:
        try:
            json_doc = Syntax(text, "json", line_numbers=True)
            self.update(json_doc)
            return True
        except:
            return False

class JSONTree(Tree):
    def __init__(self, id):
        super().__init__("JSON", id=id)
        self.show_root = False
        self.highlighter = ReprHighlighter()
    
    def load(self, text: str) -> None:
        self.clear()
        json_data = json.loads(text)
        self.add_node(self.root, json_data)

    def add_node(self, parent: TreeNode, data: object, name: Text|str = "") -> None:
        node = parent.add(name)
        if isinstance(data, dict):
            node._label.append("{}")
            for key, value in data.items():
                self.add_node(node, value, Text.assemble((key, 'b'), ": "))
        elif isinstance(data, list):
            node._label.append("[]")
            for index, value in enumerate(data):
                self.add_node(node, value)
        else:
            node._label.append(self.highlighter(repr(data)))
            node._allow_expand = False

    def on_resize(self, event: Resize):
        self.expand_fit(event.virtual_size.height)

    def expand_fit(self, height):
        q = self.visible_nodes()
        while height and next(q, None):
            height -= 1
        q = self.visible_nodes()
        while height and (node := next(q, None)):
            open_h = len(node._children)
            if not node.is_expanded and node._allow_expand and height >= open_h:
                node.expand()
                height -= open_h

    def visible_nodes(self):
        q = deque(self.root._children)
        while q:
            node = q.popleft()
            yield node
            if node.is_expanded:
                for child in node._children:
                    q.append(child)
