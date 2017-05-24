'''
################################## server.py #############################
# Wallet Encryption GRPC Service encrypts credit/debit cards data and
# decrypts token back to plain text card detail. It uses Fernet symmetric
# encryption library.
# Fernet: https://cryptography.io/en/latest/fernet/
################################## server.py #############################
'''
import time
import grpc
import wallet_pb2
import wallet_pb2_grpc

from concurrent import futures
from cryptography.fernet import Fernet

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

class WalletServicer(wallet_pb2.WalletServicer):
    '''
    WalletServicer is the main class that handles Fernet encryption and decryption.
    '''
    

    def __init__(self):
        '''
        Generates a Ferent key and saves it into an instance variable so that
        it can be re-used at encryption and decryption.
        Initializes Ferent instance and saves it into another instance variable.
        '''
        # TODO
        key = Fernet.generate_key()
        self.cipher_suite = Fernet(key)


    def encrypt(self, request, context):
        '''
        Encrypts the card detail from the request.card using Fernet.
        :param self: self reference
        :param request: request object
        :param context: the request context
        :return: return a protocol buffer card encrypted response with token
        :rtype: wallet_pb2.CardEncryptResponse
        '''
        # TODO

        return wallet_pb2.CardEncryptResponse(token=self.cipher_suite.encrypt(bytes(request.card)))


    def decrypt(self, request, context):
        '''
        Decrypts the token from the request.token using Fernet.
        :param self: self reference
        :param request: request object
        :param context: the request context
        :return: return a protocol buffer card decrypted response with card_in_plain_text
        :rtype: wallet_pb2.CardDecryptResponse
        '''
        # TODO
        return wallet_pb2.CardDecryptResponse(card_in_plain_text= self.cipher_suite.decrypt(bytes(request.token)))

def run(host, port):
    '''
    Run the GRPC server
    '''
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    wallet_pb2_grpc.add_WalletServicer_to_server(WalletServicer(), server)
    server.add_insecure_port('%s:%d' % (host, port))
    server.start()

    try:
        while True:
            print "Server started at...%d" % port
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    run('0.0.0.0', 3000)
