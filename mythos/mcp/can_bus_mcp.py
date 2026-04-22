"""
can-bus-mcp — automotive CAN-bus + UDS (ISO 14229) wrapper (§9.2 / §7 frontier).

Uses the optional ``python-can`` package.  Without it every tool returns
``available=False`` so the agent can route around cleanly.
"""

from __future__ import annotations

from typing import Any

from ._mcp_runtime import MCPServer

server = MCPServer(name="can-bus-mcp")

try:
    import can  # type: ignore
    _CAN = True
except Exception:  # noqa: BLE001
    _CAN = False


def _gate() -> dict[str, Any] | None:
    if not _CAN:
        return {"available": False, "reason": "python-can not installed"}
    return None


@server.tool("send_frame",
             schema={"interface": "string", "channel": "string",
                     "arb_id": "int", "data_hex": "string"})
def send_frame(interface: str, channel: str, arb_id: int, data_hex: str) -> dict[str, Any]:
    if (g := _gate()):
        return g
    bus = can.interface.Bus(interface=interface, channel=channel)
    msg = can.Message(arbitration_id=arb_id, data=bytes.fromhex(data_hex), is_extended_id=False)
    bus.send(msg, timeout=2.0)
    return {"sent": True, "arb_id": arb_id}


@server.tool("listen", schema={"interface": "string", "channel": "string", "seconds": "int"})
def listen(interface: str, channel: str, seconds: int = 5) -> dict[str, Any]:
    if (g := _gate()):
        return g
    import time
    bus = can.interface.Bus(interface=interface, channel=channel)
    end, frames = time.time() + seconds, []
    while time.time() < end:
        msg = bus.recv(timeout=0.5)
        if msg:
            frames.append({"arb_id": msg.arbitration_id,
                           "data": bytes(msg.data).hex(),
                           "ts": msg.timestamp})
    return {"frames": frames, "count": len(frames)}


@server.tool("uds_request",
             schema={"interface": "string", "channel": "string",
                     "arb_id": "int", "service_id": "int", "sub_function": "int (optional)"})
def uds_request(interface: str, channel: str, arb_id: int,
                service_id: int, sub_function: int = -1) -> dict[str, Any]:
    if (g := _gate()):
        return g
    payload = bytes([service_id]) + (bytes([sub_function]) if sub_function >= 0 else b"")
    bus = can.interface.Bus(interface=interface, channel=channel)
    msg = can.Message(arbitration_id=arb_id,
                      data=bytes([len(payload)]) + payload,
                      is_extended_id=False)
    bus.send(msg, timeout=2.0)
    resp = bus.recv(timeout=2.0)
    return {"sent_service": hex(service_id),
            "response": (bytes(resp.data).hex() if resp else None)}


if __name__ == "__main__":
    server.serve_stdio()
