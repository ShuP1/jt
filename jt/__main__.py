from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Input

from .widgets import JSONDocument, JSONTree
from .loader import load_file, close_pipe

class JustTreeApp(App):
    TITLE = "jt"
    CSS = """
    #tree-view {
        background: $panel;
        border-right: wide $background;
        dock: left;
        width: 0.5fr;
        overflow-x: auto;
    }

    #json-document {
        height: auto;
    }

    #command {
        border: none;
    }
    """

    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("ctrl+s", "app.screenshot()", "Screenshot"),
    ]

    def __init__(self):
        super().__init__()
        self.file = load_file()
    def __del__(self):
        self.file.close()

    def compose(self) -> ComposeResult:
        yield Container(
            JSONTree(id="tree-view"),
            JSONDocument(id="json-document"),
        )
        yield Input(id="command", placeholder="command")

    def on_mount(self) -> None:
        text_data = self.file.read()

        json_doc = self.query_one(JSONDocument)
        json_doc.load(text_data)

        tree = self.query_one(JSONTree)
        tree.load(text_data)
        tree.focus()
        tree.action_page_down()

    def on_input_submitted(self, msg: Input.Submitted) -> None:
        if msg.value:
            self.log.error(msg.value)
        msg.input.value = ''

def main():
    app = JustTreeApp()
    app.run()
    close_pipe()

if __name__ == "__main__":
    main()
