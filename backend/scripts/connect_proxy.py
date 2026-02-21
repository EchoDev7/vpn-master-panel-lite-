#!/usr/bin/env python3
"""Minimal HTTP CONNECT proxy.

Purpose:
- Provide an optional, panel-managed CONNECT proxy for OpenVPN HTTP proxy camouflage.
- Locked down by default: only allows CONNECT to a configured target (e.g. 127.0.0.1:443).

This is intentionally small and dependency-free (asyncio only).
"""

import argparse
import asyncio
import logging
from typing import Tuple


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s connect-proxy: %(message)s",
)


def _parse_hostport(value: str) -> Tuple[str, int]:
    if ":" not in value:
        raise ValueError("expected host:port")
    host, port_s = value.rsplit(":", 1)
    port = int(port_s)
    if not (1 <= port <= 65535):
        raise ValueError("invalid port")
    if not host:
        raise ValueError("invalid host")
    return host, port


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    *,
    allowed_target: Tuple[str, int],
    timeout: float,
) -> None:
    peer = client_writer.get_extra_info("peername")
    try:
        # Read request line
        req_line = await asyncio.wait_for(client_reader.readline(), timeout=timeout)
        if not req_line:
            return

        try:
            line = req_line.decode("utf-8", "replace").strip("\r\n")
            parts = line.split()
            if len(parts) < 3:
                raise ValueError("bad request line")
            method, target, _httpver = parts[0].upper(), parts[1], parts[2]
        except Exception:
            client_writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await client_writer.drain()
            return

        # Consume headers until blank line
        while True:
            h = await asyncio.wait_for(client_reader.readline(), timeout=timeout)
            if not h or h in (b"\r\n", b"\n"):
                break

        if method != "CONNECT":
            client_writer.write(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            await client_writer.drain()
            return

        try:
            dst_host, dst_port = _parse_hostport(target)
        except Exception:
            client_writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await client_writer.drain()
            return

        if (dst_host, dst_port) != allowed_target:
            logging.warning("blocked target=%s from=%s allowed=%s:%s", target, peer, allowed_target[0], allowed_target[1])
            client_writer.write(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            await client_writer.drain()
            return

        # Connect to target
        try:
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(dst_host, dst_port),
                timeout=timeout,
            )
        except Exception as exc:
            logging.warning("connect failed target=%s from=%s err=%s", target, peer, exc)
            client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            await client_writer.drain()
            return

        client_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        await client_writer.drain()

        await asyncio.gather(
            _pipe(client_reader, remote_writer),
            _pipe(remote_reader, client_writer),
        )

    except asyncio.TimeoutError:
        try:
            client_writer.write(b"HTTP/1.1 408 Request Timeout\r\n\r\n")
            await client_writer.drain()
        except Exception:
            pass
    except Exception as exc:
        logging.exception("unhandled error from=%s err=%s", peer, exc)
    finally:
        try:
            client_writer.close()
            await client_writer.wait_closed()
        except Exception:
            pass


async def main_async(listen_host: str, listen_port: int, allowed_target: Tuple[str, int], timeout: float) -> None:
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, allowed_target=allowed_target, timeout=timeout),
        host=listen_host,
        port=listen_port,
        reuse_port=True,
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in (server.sockets or []))
    logging.info("listening on %s; allowed CONNECT=%s:%s", addrs, allowed_target[0], allowed_target[1])

    async with server:
        await server.serve_forever()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--listen-host", default="0.0.0.0")
    p.add_argument("--listen-port", type=int, required=True)
    p.add_argument(
        "--allowed-target",
        required=True,
        help="Only allow CONNECT to this host:port (example: 127.0.0.1:443)",
    )
    p.add_argument("--timeout", type=float, default=10.0)
    args = p.parse_args()

    if not (1 <= args.listen_port <= 65535):
        raise SystemExit("invalid listen port")

    allowed_target = _parse_hostport(args.allowed_target)

    asyncio.run(main_async(args.listen_host, args.listen_port, allowed_target, args.timeout))


if __name__ == "__main__":
    main()
