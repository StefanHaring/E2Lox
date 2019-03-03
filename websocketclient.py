#Imports - standard Pyhton library
import hmac                        #Authentication
from hashlib import sha1           #Authentication 
from hashlib import md5
import logging                     #Logging
import select                      #Check if socket is readable
import struct                      #Parsing structure
import urllib2                     #Authentication 
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
import urllib
import json                        #Parsing JSON 
import base64

#Imports - websocket 
from websocket import create_connection

#Constants
CMD_GETPUBLICKEY = 'jdev/sys/getPublicKey'

WS_BIN_HDR_STRUCT              = 'c c 2c I'
WS_BIN_EV_DATA_STRUCT          = 'l H H 8s d'

WS_BIN_EV_DATA_LENGTH = 24

WS_DT_TEXT      = 0x00  #Textmessage
WS_DT_FILE      = 0x01  #angeforderte Datei
WS_DT_EVENT     = 0x02  #Eventdaten
WS_DT_EVENTTEXT = 0x03  #Texteventdaten
WS_DT_DAYTIMER  = 0x04  #Schaltuhreventdaten

WS_CMD_ENC                  = 'jdev/sys/enc/{}'
WS_CMD_GETKEY2              = 'jdev/sys/getkey2/admin'
WS_CMD_GETTOKEN             = 'jdev/sys/gettoken/' 
WS_CMD_LOX_APP_VERSION      = 'jdev/sps/LoxAPPversion3'
WS_CMD_ENABLE_STATUS_UPDATE = 'dev/sps/enablestatusupdate' 
WS_CMD_STRUCTURE_FILE       = 'data/LoxAPP3.json'
WS_CMD_CONTROL_COMMAND      = 'jdev/sps/io/{}'
WS_CMD_SECURED_DETAILS      = 'jdev/sps/io/{}/securedDetails'
WS_CMD_KEYEXCHANGE          = 'jdev/sys/keyexchange/{}'

WS_RESPONSE_LL                = 'LL'
WS_RESPONSE_ATTRIBUTE_CONTROL = 'control'
WS_RESPONSE_ATTRIBUTE_VALUE   = 'value'
WS_RESPONSE_ATTRIBUTE_CODE    = 'Code'
WS_RESPONSE_CODE_VALID        = 200

TCP_TIMEOUT     = 5

ENCODING_UTF8 = 'utf8'

BLOCK_SIZE = 16  # Bytes
pad_zeropadding = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(0)

class AESCipher:
    def __init__( self, key, iv):
        self._aes_cipher = AES.new(key, AES.MODE_CBC, iv)

    def encrypt( self, raw ):
        raw = pad_zeropadding(raw)
        return self._aes_cipher.encrypt(raw)

class WebSocketClientException(Exception):
    def __init__(self, msg = ''):
        self._msg = msg
    def __str__(self):
        return repr(self._msg)
      
class WebSocketClient:        
    def __init__(self, connection_configuration, on_status_update):
        self._logger = logging.getLogger('WebSocketClient')
        self._connection_configuration = connection_configuration 
         
        self._ws = None
        self._publickey = ''
        self._key  = ''
        self._salt = ''
        self._aes_key = ''
        self._aes_iv = ''
        self._aes_cipher = None     
        self.connect()
        self._on_status_update = on_status_update        
        
    def connect(self):
        try:          
            
            #Get Public Key
            self._get_public_key()
            
            #Generate AES key and iv 
            self._aes_key = self._generate_aes_key()
            self._aes_iv = self._generate_aes_iv()
        
            #Generate session key
            sessionkey = self._generate_session_key() 

            #Create WebSocket             
            self._ws = create_connection("ws://{}/ws/rfc6455".format(self._connection_configuration.ipaddress))

            #Key exchange
            self.write_websocket_msg_waited(WS_CMD_KEYEXCHANGE.format(sessionkey))            

            #Get auth key and salt 
            self._get_auth_key_and_salt()

            #Hash user and password 
            hmac = self._hash_pw(self._key, self._salt, self._connection_configuration.username, self._connection_configuration.password)

            #Generate AES cipher
            self._aes_cipher = AESCipher(self._aes_key, self._aes_iv)

            #Request token
            message = WS_CMD_GETTOKEN + hmac + "/{}/2/0edfc5f9a-df3f-4cad-9dddcdc42c732be2/nodeloxwsapi".format(self._connection_configuration.username) 
                                    		        
            self.write_encrypted_websocket_waited(message)

        except:
            self._connection_error('Socket connect failed!')

    def _hash_pw(self, key, salt, user, pw):
        pwhash = sha1('{}:{}'.format(pw, salt)).hexdigest().upper()
        return hmac.new(key, '{}:{}'.format(
               user, pwhash), sha1).hexdigest().upper()

    def _get_public_key(self):
        resp = urllib2.urlopen('http://{}:{}/{}'.format(self._connection_configuration.ipaddress, self._connection_configuration.port, CMD_GETPUBLICKEY)).read()
        self._publickey = self._parse_response(CMD_GETPUBLICKEY, resp)
        self._publickey = self._publickey.replace('CERTIFICATE', 'PUBLIC KEY')
        self._publickey = self._publickey.replace('BEGIN PUBLIC KEY-----', 'BEGIN PUBLIC KEY-----\n')
        self._publickey = self._publickey.replace('-----END PUBLIC KEY', '\n-----END PUBLIC KEY')
                   
    def _get_auth_key_and_salt(self):
        value = self.write_websocket_msg_waited(WS_CMD_GETKEY2)
        self._key = value['key'].decode('hex')
        self._salt = value['salt']
      
    def _generate_aes_iv(self):
        return Random.get_random_bytes(16)
        
    def _generate_aes_key(self):
        return md5('1234'.encode('utf8')).hexdigest()
        
    def _generate_session_key(self):
        cipher = Cipher_PKCS1_v1_5.new(RSA.importKey(self._publickey))
        enc_session_key = cipher.encrypt(self._aes_key + b':' + self._aes_iv)
        return base64.b64encode(enc_session_key)
                          
    def close(self):
        if(self._ws is not None):
            self._ws.close()
                                        
    def write_encrypted_websocket_msg(self, msg):
        message = 'salt/{}/{}'.format(self._salt, msg)

        aesmessage = self._aes_cipher.encrypt(message)
                        
        aesmessage = base64.b64encode(aesmessage)
        aesmessage = urllib.quote(aesmessage.encode("utf-8"))
        self.write_websocket_msg(WS_CMD_ENC.format(aesmessage))

        
    def write_websocket_msg(self, msg):
        self._ws.send(msg)

    def write_encrypted_websocket_waited(self, msg):
        self._logger.debug('write_encrypted_websocket_waited: <{}>'.format(msg))

        self.write_encrypted_websocket_msg(msg)
        resp = self._read_msg_waited()
        return self._parse_response(msg, resp)        

    def write_websocket_msg_waited(self, msg):
        self.write_websocket_msg(msg)
        resp = self._read_msg_waited()
        return self._parse_response(msg, resp)        
 
    def _parse_response(self, msg, response):
        resp = response.replace('code', WS_RESPONSE_ATTRIBUTE_CODE)
        resp_json = json.loads(resp)    

        if(msg.find(resp_json[WS_RESPONSE_LL][WS_RESPONSE_ATTRIBUTE_CONTROL]) == ''):
            self._connection_error('Invalid response! Control not correct!')
             
        try:
            code = int(resp_json[WS_RESPONSE_LL][WS_RESPONSE_ATTRIBUTE_CODE])
        except ValueError:
            self._connection_error('Invalid response! Code is not a number!')
                                
        if(code != WS_RESPONSE_CODE_VALID):
            self._connection_error('Invalid response! Response status invalid!')
                    
        return resp_json[WS_RESPONSE_LL][WS_RESPONSE_ATTRIBUTE_VALUE]
        
    def _connection_error(self, msg):
        self.close()
        raise WebSocketClientException(msg)
       
    def get_app_version(self):
        return self.write_websocket_msg_waited(WS_CMD_LOX_APP_VERSION)

    def get_structure_file(self):
        self.write_websocket_msg(WS_CMD_STRUCTURE_FILE)
        self._ws.recv()
                      
        return self._read_msg_waited() 
        
    def enable_status_update(self):
        self.write_websocket_msg(WS_CMD_ENABLE_STATUS_UPDATE)
        
    def send_command(self, command):
        return self.write_websocket_msg_waited(WS_CMD_CONTROL_COMMAND.format(command))
               
    def get_secured_details(self, uuid):
        return self.write_websocket_msg_waited(WS_CMD_SECURED_DETAILS.format(uuid))
    
    def get_image(self, image):
        self.write_websocket_msg(image)
        return self._read_msg_waited() 
                                      
    def _read_msg_waited(self, timeout = TCP_TIMEOUT):
        return self._read_msg_internal(timeout, waited = True)
    
    def _read_msg_internal(self, timeout = TCP_TIMEOUT, waited = False):
        self._logger.debug('Read msg internal: timeout: <{}>, waited: <{}>'.format(timeout, waited))
        
        while(True):
            input_ready, output_ready, except_ready = select.select([self._ws.sock],[],[], timeout)
        
            if(len(input_ready) == 0) or (input_ready[0] != self._ws.sock):
                return None
        
            str = self._ws.recv()
            
            if((len(str) == 0) and waited == False):
                return None
       
            elif(len(str) == 0): 
                self._logger.debug('Read msg internal: No message reveived')
                raise WebSocketClientException('No message reveived!')
        
            header_data_array = str 
        
            #message received - parse header
            header_data = struct.unpack_from(WS_BIN_HDR_STRUCT, header_data_array, 0)
                        
            content_data_array = self._ws.recv()
            
            self._logger.debug('Read msg internal: Message received: <{}>'.format, content_data_array)
                        
            #Text received
            if(int(header_data[1].encode('hex'), 16) == WS_DT_TEXT):
                self._logger.debug('Read msg internal: text received: <{}>'.format(content_data_array))
                return content_data_array 
                
            #File received
            if(int(header_data[1].encode('hex'), 16) == WS_DT_FILE):
                return content_data_array 
               
            #Event received
            elif(int(header_data[1].encode('hex'), 16) == WS_DT_EVENT): 
                index = 0
                while index < header_data[4] / WS_BIN_EV_DATA_LENGTH:
                    #Convert string to struct-array
                    event_data = struct.unpack_from(WS_BIN_EV_DATA_STRUCT, content_data_array, index * WS_BIN_EV_DATA_LENGTH)

                    # calculate UUID
                    uuid1 = hex(event_data[0])
                    uuid1 = uuid1[2:len(uuid1)].zfill(8)

                    uuid2 = hex(event_data[1])
                    uuid2 = uuid2[2:len(uuid2)].zfill(4)

                    uuid3 = hex(event_data[2])
                    uuid3 = uuid3[2:len(uuid3)].zfill(4)

                    uuid4 = event_data[3].encode('hex')

                    eventUUID = "-".join([uuid1, uuid2, uuid3, uuid4])
                    
                    # Get event value
                    eventValue = event_data[4]
                    index += 1  

                    if(self._on_status_update is not None):
                        self._on_status_update(eventUUID, eventValue)    
                
    def execute(self):
        while (True):
            if(self._read_msg_internal(0, False) is None):
                break
            
