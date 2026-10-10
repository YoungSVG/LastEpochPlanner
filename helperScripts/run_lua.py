"""Run a Lua script with the bundled Windows LuaJIT DLL (no GUI required)."""
import ctypes
from pathlib import Path
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python helperScripts/run_lua.py SCRIPT.lua")
    dll = Path(__file__).resolve().parents[1] / "runtime" / "lua51.dll"
    lua = ctypes.CDLL(str(dll))
    lua.luaL_newstate.restype = ctypes.c_void_p
    lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
    lua.luaL_loadfile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lua.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
    lua.lua_tolstring.restype = ctypes.c_char_p
    lua.lua_close.argtypes = [ctypes.c_void_p]
    state = lua.luaL_newstate()
    if not state:
        raise MemoryError("Could not create Lua state")
    try:
        lua.luaL_openlibs(state)
        status = lua.luaL_loadfile(state, str(Path(sys.argv[1]).resolve()).encode())
        if status == 0:
            status = lua.lua_pcall(state, 0, -1, 0)
        if status:
            error = lua.lua_tolstring(state, -1, None)
            raise SystemExit(error.decode(errors="replace") if error else "Lua error")
    finally:
        lua.lua_close(state)


if __name__ == "__main__":
    main()
