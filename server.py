"""Wallet encryption gRPC service.

Encrypts card data with Fernet and decrypts a token back to the card's
protobuf text format. Fernet: https://cryptography.io/en/latest/fernet/
"""

import os
from concurrent import futures

import grpc
from cryptography.fernet import Fernet

import wallet_pb2
import wallet_pb2_grpc


class WalletServicer(wallet_pb2_grpc.WalletServicer):
    """Fernet encryption and decryption for the Wallet service.

    The key is generated in memory when the servicer is constructed. Restarting
    the process throws that key away, so tokens from a previous process cannot
    be decrypted.
    """

    def __init__(self):
        self.cipher_suite = Fernet(Fernet.generate_key())

    def encrypt(self, request, context):
        """Encrypt ``request.card`` and return a token.

        The plaintext is ``str(card)`` encoded as UTF-8: the protobuf text
        format the midterm decrypts back to. Python 2's ``bytes(card)``
        produced that text. On Python 3, ``bytes(card)`` raises ``TypeError``.
        """
        plaintext = str(request.card).encode("utf-8")
        token = self.cipher_suite.encrypt(plaintext).decode("ascii")
        return wallet_pb2.CardEncryptResponse(token=token)

    def decrypt(self, request, context):
        """Decrypt ``request.token`` and return the card text.

        A token from another key, or a tampered token, raises
        ``cryptography.fernet.InvalidToken``. gRPC surfaces that as status
        UNKNOWN.
        """
        plaintext = self.cipher_suite.decrypt(request.token.encode("ascii"))
        return wallet_pb2.CardDecryptResponse(
            card_in_plain_text=plaintext.decode("utf-8")
        )


def create_server(host, port):
    """Bind a wallet server to ``host:port`` without starting it.

    ``port`` 0 asks the OS for an ephemeral port. Returns ``(server, bound_port)``.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    wallet_pb2_grpc.add_WalletServicer_to_server(WalletServicer(), server)
    bound_port = server.add_insecure_port(f"{host}:{port}")
    if bound_port == 0:
        raise RuntimeError(f"Failed to bind {host}:{port}")
    return server, bound_port


def run(host, port):
    """Start the server and block until Ctrl-C."""
    server, bound_port = create_server(host, port)
    server.start()
    print(f"Server started at...{bound_port}", flush=True)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    host = os.environ.get("WALLET_HOST", "0.0.0.0")
    port = int(os.environ.get("WALLET_PORT", "3000"))
    run(host, port)
