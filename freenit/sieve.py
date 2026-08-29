from __future__ import annotations

import asyncio
import logging

log = logging.getLogger("sieve")


class ManageSieveClient:
    def __init__(self, host: str, port: int, token: str):
        self._host = host
        self._port = port
        self._token = token
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def __aenter__(self) -> "ManageSieveClient":
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        ok, _ = await self._read_response()
        if not ok:
            raise RuntimeError("ManageSieve greeting failed")
        cmd = f'AUTHENTICATE "PLAIN" "{self._token}"\r\n'
        self._writer.write(cmd.encode())
        await self._writer.drain()
        ok, lines = await self._read_response()
        if not ok:
            log.warning("ManageSieve auth failed: %s", lines)
            raise RuntimeError("ManageSieve authentication failed")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._writer is not None:
            try:
                self._writer.write(b"LOGOUT\r\n")
                await self._writer.drain()
                await self._read_response()
            except Exception as e:
                log.warning("ManageSieve LOGOUT error: %s", e)
            finally:
                self._writer.close()
                try:
                    await self._writer.wait_closed()
                except Exception as e:
                    log.warning("ManageSieve wait_closed error: %s", e)

    async def _read_response(self) -> tuple[bool, list[str]]:
        lines: list[str] = []
        while True:
            raw = await self._reader.readline()
            line = raw.decode(errors="replace").rstrip("\r\n")

            if line.startswith("{") and (line.endswith("}") or line.endswith("+}")):
                inner = line.lstrip("{").rstrip("}").rstrip("+")
                try:
                    size = int(inner)
                except ValueError:
                    lines.append(line)
                    continue
                data = await self._reader.readexactly(size)
                await self._reader.readline()
                lines.append(data.decode(errors="replace"))
                continue

            lines.append(line)
            upper = line.upper()
            if upper.startswith("OK"):
                return True, lines
            if upper.startswith("NO") or upper.startswith("BYE"):
                return False, lines

    async def list_scripts(self) -> list[dict]:
        self._writer.write(b"LISTSCRIPTS\r\n")
        await self._writer.drain()
        ok, lines = await self._read_response()
        if not ok:
            log.warning("ManageSieve LISTSCRIPTS failed: %s", lines)
            raise RuntimeError("LISTSCRIPTS failed")
        scripts = []
        for line in lines:
            upper = line.upper()
            if upper.startswith("OK"):
                break
            active = "ACTIVE" in upper
            name_part = line.split(" ACTIVE")[0].split(" active")[0].strip()
            name = name_part.strip('"')
            if name:
                scripts.append({"name": name, "active": active})
        return scripts

    async def get_script(self, name: str) -> tuple[str, bool]:
        cmd = f'GETSCRIPT "{name}"\r\n'
        self._writer.write(cmd.encode())
        await self._writer.drain()
        ok, lines = await self._read_response()
        if not ok:
            log.warning("ManageSieve GETSCRIPT %r failed: %s", name, lines)
            raise RuntimeError(f"GETSCRIPT {name!r} failed")
        content = ""
        for line in lines:
            if line.upper().startswith("OK"):
                break
            content = line
        scripts = await self.list_scripts()
        active = any(s["name"] == name and s["active"] for s in scripts)
        return content, active

    async def put_script(self, name: str, content: str) -> None:
        encoded = content.encode()
        size = len(encoded)
        header = f'PUTSCRIPT "{name}" {{{size}+}}\r\n'
        self._writer.write(header.encode() + encoded + b"\r\n")
        await self._writer.drain()
        ok, lines = await self._read_response()
        if not ok:
            log.warning("ManageSieve PUTSCRIPT %r failed: %s", name, lines)
            raise RuntimeError(f"PUTSCRIPT {name!r} failed")

    async def delete_script(self, name: str) -> None:
        cmd = f'DELETESCRIPT "{name}"\r\n'
        self._writer.write(cmd.encode())
        await self._writer.drain()
        ok, lines = await self._read_response()
        if not ok:
            log.warning("ManageSieve DELETESCRIPT %r failed: %s", name, lines)
            raise RuntimeError(f"DELETESCRIPT {name!r} failed")

    async def set_active(self, name: str) -> None:
        cmd = f'SETACTIVE "{name}"\r\n'
        self._writer.write(cmd.encode())
        await self._writer.drain()
        ok, lines = await self._read_response()
        if not ok:
            log.warning("ManageSieve SETACTIVE %r failed: %s", name, lines)
            raise RuntimeError(f"SETACTIVE {name!r} failed")
