"""``dynamic-analysis-mcp`` — AFL++, KLEE, QEMU, Frida, GDB."""

from __future__ import annotations

from ._mcp_runtime import MCPServer
from ..dynamic.aflpp_runner import AFLPlusPlusRunner
from ..dynamic.klee_runner import KLEERunner
from ..dynamic.qemu_harness import QEMUHarness
from ..dynamic.frida_instr import FridaInstrumenter
from ..dynamic.gdb_automation import GDBAutomation

server = MCPServer("dynamic-analysis-mcp")
_afl = AFLPlusPlusRunner()
_klee = KLEERunner()
_qemu = QEMUHarness()
_frida = FridaInstrumenter()
_gdb = GDBAutomation()


@server.tool("afl_run",   {"harness_dir": "string"})
def afl_run(harness_dir: str):  return _afl.run(harness_dir)
@server.tool("klee_run",  {"harness_dir": "string"})
def klee_run(harness_dir: str): return _klee.run(harness_dir)
@server.tool("qemu_run",  {"harness_dir": "string"})
def qemu_run(harness_dir: str): return _qemu.run(harness_dir)
@server.tool("frida_attach", {"harness_dir": "string"})
def frida_attach(harness_dir: str): return _frida.attach_all(harness_dir)
@server.tool("gdb_replay", {"crash": "object"})
def gdb_replay(crash: dict):    return _gdb.replay(crash)


if __name__ == "__main__":  # pragma: no cover
    server.serve_stdio()
