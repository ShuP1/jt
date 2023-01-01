import sys, os, platform, tempfile, subprocess
from io import TextIOWrapper

def load_file() -> TextIOWrapper:
    file = sys.stdin
    if len(sys.argv) > 1:
        if os.path.isfile(path := sys.argv[1]):
            try:
                file = open(path, 'r+')
            except:
                file = open(path)
        else:
            file = tempfile.TemporaryFile('r+')
            file.write(subprocess.check_output(('jc', '-p', *sys.argv[1:]), text=True))
            file.seek(0)
    if file.isatty():
        file.close()
        file = tempfile.TemporaryFile('r+')
        file.write('null')
        file.seek(0)
    # See:Textualize/textual/issues/153#issuecomment-1256933121
    if platform.system() != "Windows":
        sys.stdin = open('/dev/tty', 'r')
    return file

def close_pipe():
    if not sys.stdin.closed:
        sys.stdin.close()
