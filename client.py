"""Wallet client.

Calls a remote Wallet service to encrypt card data and decrypt a token.
"""

import grpc

import wallet_pb2
import wallet_pb2_grpc


class WalletClient:
    """Encrypts and decrypts card info through a gRPC stub."""

    def __init__(self, host="0.0.0.0", port=3000):
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = wallet_pb2_grpc.WalletStub(self.channel)

    def encrypt(self, plain_text):
        """Encrypt a card dict.

        ``plain_text`` keys are ``card_holder_name``, ``card_number``, and
        ``card_expiry_yyyymm``. Returns ``wallet_pb2.CardEncryptResponse``.
        """
        card = wallet_pb2.Card(
            card_holder_name=plain_text["card_holder_name"],
            card_number=plain_text["card_number"],
            card_expiry_yyyymm=plain_text["card_expiry_yyyymm"],
        )
        return self.stub.encrypt(wallet_pb2.CardEncryptRequest(card=card))

    def decrypt(self, token):
        """Decrypt ``token``. Returns ``wallet_pb2.CardDecryptResponse``."""
        return self.stub.decrypt(wallet_pb2.CardDecryptRequest(token=token))
