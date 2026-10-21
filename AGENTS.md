# Agent guide

CMPE 273 midterm (May 2017): a flat Python gRPC service that Fernet-encrypts a card. Human overview, course context, and how to run it are in [README.md](README.md). This file is the contract and the commands.

## Architecture

- `wallet.proto` defines `Wallet.encrypt` and `Wallet.decrypt`. RPC names are lowercase. Field numbers are part of the contract. Do not rename them.
- `client.py` `WalletClient` maps a dict to `Card` / `CardEncryptRequest` and calls the stub. Default target is `0.0.0.0:3000`, matching `python server.py`.
- `server.py` `WalletServicer` owns one in-memory Fernet key, created in `__init__`. `create_server(host, port)` binds but does not start. `run()` starts and blocks. `port` 0 is an ephemeral port and is what the tests use.
- The server has `max_workers=1`. Leave that unless you are deliberately changing concurrency.
- The channel is insecure gRPC. TLS, authentication, and a persisted key were outside the assignment. Leave them out unless the owner asks.

## Plaintext contract

`encrypt` encrypts `str(request.card).encode("utf-8")`. `str(card)` is the protobuf **text** format. Decrypt returns that text in `card_in_plain_text`.

Keep this as text. `SerializeToString()` would still round-trip inside one process and would change the midterm's observable result. The sample card decrypts to exactly

```text
card_holder_name: "Foo Bar"
card_number: "4012888888881881"
card_expiry_yyyymm: 201804
```

That string is 87 bytes. Fernet overhead plus PKCS7 padding makes the token **204** characters. `test.py` asserts both. Python 2's `bytes(card)` happened to be this text. On Python 3, `bytes(card)` raises `TypeError` because `Card` has no `__bytes__`.

Proto3 text format drops default values and escapes quotes. Keep using `str(card)` so that behavior stays with protobuf, not a hand-rolled formatter.

A bad or foreign token raises `cryptography.fernet.InvalidToken` inside the servicer. The gRPC client sees status `UNKNOWN`. Do not swallow that unless you are also changing the tests.

## Layout

| Path | Role |
| --- | --- |
| `server.py`, `client.py`, `test.py` | Hand-written. Run from the repo root so imports resolve. |
| `wallet.proto` | Source of truth for the messages. |
| `wallet_pb2.py`, `wallet_pb2_grpc.py` | Generated. Do not edit. Checked in on purpose. |
| `requirements.txt` | Pinned runtime: `grpcio==1.84.0`, `protobuf==7.36.2`, `cryptography==50.0.2`. |
| `requirements-dev.txt` | Adds `grpcio-tools==1.84.0` and `ruff==0.17.0`. |
| `pyproject.toml` | Ruff config only. The repo is a set of scripts, not a package. |
| `.github/workflows/ci.yml` | Lint, format check, `python -m unittest test` on Python 3.11, 3.12, and 3.13. |

Ruff excludes the generated files. They carry a `NO CHECKED-IN PROTOBUF GENCODE` banner from protoc. Ignore the banner.

## Commands

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

ruff check .
ruff format .
python -m unittest test -v
python server.py
```

Regenerate stubs only when the proto or the pinned `grpcio-tools` changes, then commit the generated files with the dependency bump:

```sh
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. wallet.proto
```

`wallet_pb2_grpc.py` requires `grpcio>=1.84.0`. `wallet_pb2.py` requires `protobuf>=7.35.1`. Bumping either without regenerating, or regenerating without bumping the pins, will fail at import.

## Conventions

- Python 3.11+. `cryptography` 50's wheels do not support 3.10. No `from __future__` imports, no Python 2.
- Ruff is the formatter and linter (line length 88, rules E, F, I, UP). Match it instead of restyling by hand.
- Tests are `unittest` in `test.py`. They must pass with no server already running.
- `4012888888881881` is the assignment's public test PAN. Keep it in tests and examples. It is not a secret.
- There is no license file. Do not add one.

## Gotchas

- Imports are top-level (`import wallet_pb2`). Running from another directory fails. CI and docs assume the repo root.
- The Fernet key dies with the process. A token in the old README cannot be decrypted by a server you start now.
- `WalletClient()` with no arguments talks to port 3000. Tests pass `127.0.0.1` and the bound ephemeral port instead.
- `python -m test` is ambiguous with the stdlib `test` package. Use `python -m unittest test`.
- `add_insecure_port` in grpcio 1.84 raises `RuntimeError` when the address will not bind. `create_server` also rejects a return value of 0.
- Ctrl-C stops `run()` via `KeyboardInterrupt`. The startup line is `Server started at...{port}` with the ellipsis from the original assignment.
- `WALLET_HOST` and `WALLET_PORT` are optional overrides. Unset, the server is `0.0.0.0:3000`.
