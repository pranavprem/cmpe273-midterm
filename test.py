"""Tests for the wallet encryption gRPC service.

Run from the repository root:

    python -m unittest test
"""

import unittest

import grpc
from cryptography.fernet import InvalidToken

import wallet_pb2
from client import WalletClient
from server import WalletServicer, create_server

# Public Visa test PAN from the 2017 midterm. Not a real card.
SAMPLE_CARD = {
    "card_holder_name": "Foo Bar",
    "card_number": "4012888888881881",
    "card_expiry_yyyymm": 201804,
}

# Protobuf text format the original Python 2 service encrypted via bytes(card).
# 87 bytes. Fernet framing plus PKCS7 padding makes the token 204 characters.
EXPECTED_PLAINTEXT = (
    'card_holder_name: "Foo Bar"\n'
    'card_number: "4012888888881881"\n'
    "card_expiry_yyyymm: 201804\n"
)

QUOTED_PLAINTEXT = (
    'card_holder_name: "Foo \\"Bar\\""\n'
    'card_number: "4012888888881881"\n'
    "card_expiry_yyyymm: 201804\n"
)


def _request_for(card_fields):
    return wallet_pb2.CardEncryptRequest(
        card=wallet_pb2.Card(
            card_holder_name=card_fields["card_holder_name"],
            card_number=card_fields["card_number"],
            card_expiry_yyyymm=card_fields["card_expiry_yyyymm"],
        )
    )


class WalletServicerTest(unittest.TestCase):
    def test_sample_card_text_matches_midterm_contract(self):
        card = _request_for(SAMPLE_CARD).card
        self.assertEqual(str(card), EXPECTED_PLAINTEXT)
        self.assertEqual(len(EXPECTED_PLAINTEXT.encode("utf-8")), 87)

    def test_round_trip(self):
        servicer = WalletServicer()
        token = servicer.encrypt(_request_for(SAMPLE_CARD), None).token
        plain = servicer.decrypt(wallet_pb2.CardDecryptRequest(token=token), None)
        self.assertEqual(plain.card_in_plain_text, EXPECTED_PLAINTEXT)
        self.assertEqual(len(token), 204)

    def test_same_card_encrypts_to_distinct_tokens(self):
        servicer = WalletServicer()
        request = _request_for(SAMPLE_CARD)
        first = servicer.encrypt(request, None).token
        second = servicer.encrypt(request, None).token
        self.assertNotEqual(first, second)
        for token in (first, second):
            plain = servicer.decrypt(wallet_pb2.CardDecryptRequest(token=token), None)
            self.assertEqual(plain.card_in_plain_text, EXPECTED_PLAINTEXT)

    def test_quoted_name_keeps_protobuf_escaping(self):
        fields = dict(SAMPLE_CARD, card_holder_name='Foo "Bar"')
        card = _request_for(fields).card
        self.assertEqual(str(card), QUOTED_PLAINTEXT)
        servicer = WalletServicer()
        token = servicer.encrypt(_request_for(fields), None).token
        plain = servicer.decrypt(wallet_pb2.CardDecryptRequest(token=token), None)
        self.assertEqual(plain.card_in_plain_text, QUOTED_PLAINTEXT)

    def test_other_servicer_cannot_decrypt(self):
        token = WalletServicer().encrypt(_request_for(SAMPLE_CARD), None).token
        with self.assertRaises(InvalidToken):
            WalletServicer().decrypt(wallet_pb2.CardDecryptRequest(token=token), None)


class WalletClientTest(unittest.TestCase):
    def test_encrypt_requires_card_fields(self):
        client = WalletClient()
        self.addCleanup(client.channel.close)
        with self.assertRaises(KeyError):
            client.encrypt({"card_holder_name": "Foo Bar"})


class WalletGrpcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, port = create_server("127.0.0.1", 0)
        cls.server.start()
        cls.client = WalletClient(host="127.0.0.1", port=port)
        grpc.channel_ready_future(cls.client.channel).result(timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.client.channel.close()
        cls.server.stop(0).wait()

    def test_round_trip_over_grpc(self):
        first = self.client.encrypt(SAMPLE_CARD)
        second = self.client.encrypt(SAMPLE_CARD)
        self.assertEqual(len(first.token), 204)
        self.assertNotEqual(first.token, second.token)
        self.assertTrue(first.token.isascii())
        for response in (first, second):
            decrypted = self.client.decrypt(response.token)
            self.assertEqual(decrypted.card_in_plain_text, EXPECTED_PLAINTEXT)

    def test_tampered_token_is_rejected(self):
        token = self.client.encrypt(SAMPLE_CARD).token
        flipped = "A" if token[-1] != "A" else "B"
        with self.assertRaises(grpc.RpcError) as caught:
            self.client.decrypt(token[:-1] + flipped)
        self.assertEqual(caught.exception.code(), grpc.StatusCode.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
