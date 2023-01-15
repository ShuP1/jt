import lsprotocol.types as lst
from lsprotocol.converters import get_converter as get_lsprotocol
from typing import Any, Tuple, List, Generic, Type, TypeVar
from dataclasses import dataclass
import json, shutil
import asyncio
from os import getpid
from pathlib import Path
from contextlib import asynccontextmanager
from collections import deque

R = TypeVar('R')
@dataclass
class Response(Generic[R]):
    id: int
    result: R
    error: lst.ResponseError|None

    @property
    def ok(self) -> bool:
        return not self.error
    def get(self) -> R:
        assert self.ok
        return self.result
@dataclass
class Notification:
    method: str
    params: dict|list|None

class Client:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._reader = reader
        self._reader_lock = asyncio.Lock()
        self._notifications = deque()
        self._responses = dict()
        self._writer = writer
        self._req_id = 0
        self._converter = get_lsprotocol()

    @asynccontextmanager
    async def exec(args: List[str], workspaces: List[str]|str):
        assert len(args)
        proc = await asyncio.create_subprocess_exec(shutil.which(args[0]), *args[1:], stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        it = Client(proc.stdout, proc.stdin)
        if (await it.initialize(workspaces)).ok:
            yield it
        if not (await it.close()).ok:
            proc.terminate()
        await proc.wait()

    async def initialize(self, workspaces: List[str]|str) -> Response[lst.InitializeResult]:
        workspaces = [workspaces] if type(workspaces) is str else workspaces
        workspaces = [lst.WorkspaceFolder((path := Path(w).absolute()).as_uri(), path.name) for w in workspaces]
        txt_cap = lst.TextDocumentClientCapabilities(document_symbol=lst.DocumentSymbolClientCapabilities(hierarchical_document_symbol_support=True))
        res = await self.request(lst.InitializeRequest(None, lst.InitializeParams(lst.ClientCapabilities(text_document=txt_cap), process_id=getpid(), workspace_folders=workspaces)), lst.InitializeResult)
        if res.ok:
            await self.notify(lst.InitializedNotification(lst.InitializedParams()))
        return res

    async def close(self) -> Response[None]:
        res = await self.request(lst.ShutdownRequest(None))
        await self.notify(lst.ExitNotification())
        return res

    async def document_symbol(self, path: str) -> Response[List[lst.DocumentSymbol]]:
        path = Path(path).absolute().as_uri()
        for tries in range(1, 9):
            res = await self.request(lst.TextDocumentDocumentSymbolRequest(None, lst.DocumentSymbolParams(lst.TextDocumentIdentifier(path), work_done_token=None, partial_result_token=None)))
            if res.error and res.error.code == -32801:
                await asyncio.sleep(tries/10)
                continue
            if res.ok:
                res.result = [self._converter.structure(s, lst.DocumentSymbol) for s in res.result]
            break
        return res

    async def _write(self, data: Any) -> None:
        data = json.dumps(self._converter.unstructure(data)).encode()
        self._writer.writelines((
            b'Content-Length: ',
            str(len(data)).encode(),
            b'\r\n\r\n',
            data
        ))
        await self._writer.drain()
    async def notify(self, data) -> None:
        await self._write(data)
    async def request(self, request, cl: Type[R] = None) -> Response[R]:
        _id = request.id = self._req_id
        self._req_id += 1
        await self._write(request)
        while _id not in self._responses:
            await self.read()
        res = self._responses.pop(_id)
        if cl and res.ok:
            res.result = self._converter.structure(res.result, cl)
        return res
    def notified(self, method: str|None = None) -> Notification|None:
        if method is None:
            return self._notifications.popleft()
        elif t := next(filter(lambda t: t[1].method == method, enumerate(self._notifications)), None):
            i,n = t
            del self._notifications[i]
            return n

    async def read(self) -> None:
        async with self._reader_lock:
            length = 0
            while line := (await self._reader.readline()).rstrip(b'\r\n'):
                if line.startswith(b'Content-Length: '):
                    length = int(line[16:])
            msg = json.loads(await self._reader.readexactly(length))
        assert type(msg) is dict and msg.get('jsonrpc') == '2.0'

        if 'id' in msg:
            if 'error' in msg:
                self._responses[msg.get('id')] = Response(msg.get('id'), None, self._converter.structure(msg['error'], lst.ResponseError))
            else:
                self._responses[msg.get('id')] = Response(msg.get('id'), msg.get('result'), None)
        else:
            if len(self._notifications) >= 256:
                self._notifications.pop()
            self._notifications.append(Notification(msg.get('method'), msg.get('params')))

_SYMBOLS = [
    '', # None,
    '📄', # File = 1
    '📁', # Module = 2
    '📁', # Namespace = 3
    '📁', # Package = 4
    '|', # Class = 5
    '↦', # Method = 6
    '⇸', # Property = 7
    '.', # Field = 8
    '?', # Constructor = 9
    '≡', # Enum = 10
    '/', # Interface = 11
    '→', # Function = 12
    'v', # Variable = 13
    'N', # Constant = 14
    '"', # String = 15
    'n', # Number = 16
    '✓', # Boolean = 17
    '[', # Array = 18
    '{', # Object = 19
    '?', # Key = 20
    '?', # Null = 21
    '', # EnumMember = 22
    '|', # Struct = 23
    '?', # Event = 24
    '?', # Operator = 25
    '?', # TypeParameter = 26
]

async def main():
    def rec(children, indent=0):
        for d in children:
            print('  '*indent, d.name, _SYMBOLS[d.kind.value], ' ', d.selection_range, \
                ' ' + str(d.detail) if d.detail else '',
                ' ' + str(d.tags) if d.tags else '', sep='')
            if d.children:
                rec(d.children, indent+1)

    async with Client.exec(['rust-analyzer'], '/home/sheychen/Develop/Current/broot') as lsp:
        res = await lsp.document_symbol('/home/sheychen/Develop/Current/broot/src/app.rs')
        rec(res.get())

if __name__ == "__main__":
    asyncio.run(main())
