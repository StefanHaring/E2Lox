#Imports - standard Pyhton library
import ConfigParser
import socket

class ConnectionConfiguration(object):  
    def __init__(self, ipaddress, port, username, password):    
        self.ipaddress = ipaddress
        self.port = port
        self.username = username
        self.password = password
        
    @property
    def ipaddress(self):
        return self._ipaddress

    @ipaddress.setter
    def ipaddress(self, ipaddress):
        try:
            socket.inet_aton(ipaddress)
            self._ipaddress = ipaddress
        except socket.error:
            raise ValueError("IP adress is invalid")
          
    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        
        if(port < 0 or port > 65535):
            raise ValueError("Port is invalid")
        
        self._port = port
        
    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        
        if(len(username) <= 0):
            raise ValueError("Username is invalid")
        
        self._username = username
        
    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        
        if(len(password) <= 0):
            raise ValueError("Password is invalid")
        
        self._password = password

class ConfigSaver:    
    def __init__(self, config_filename):
        self._config_filename = config_filename;
        #Default Values for the connection
        self._CONNECTION_IPADDRESS_DEFAULT = '192.168.1.77'  
        self._CONNECTION_PORT_DEFAULT      = 80
        self._CONNECTION_USERNAME_DEFAULT  = 'admin'
        self._CONNECTION_PASSWORD_DEFAULT  = 'admin'
        
        self._APPVERSION_DEFAULT    = ''
    
        #Constants for the configuration file
        self._CONNECTION_SECTION          = 'CONNECTION'
        self._CONNECTION_IPADDRESS_OPTION = 'IPAddress' 
        self._CONNECTION_PORT_OPTION      = 'Port'
        self._CONNECTION_USERNAME_OPTION  = 'Username'
        self._CONNECTION_PASSWORD_OPTION  = 'Password'
        
        self._MINISERVER_SECTION          = 'MINISERVER'
        self._APPVERSION_OPTION           = 'AppVersion'
        
    def __get_option_from_config(self, config_parser, section, option, default):
        if config_parser.has_option(section, option):
            return config_parser.get(section, option)
        else:
            return default    
        
    def get_connection_configuration(self):
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(self._config_filename)
        
        #Section CONNECTION
        ipaddress = self.__get_option_from_config(config_parser, self._CONNECTION_SECTION, self._CONNECTION_IPADDRESS_OPTION, self._CONNECTION_IPADDRESS_DEFAULT) 
        port = int(self.__get_option_from_config(config_parser, self._CONNECTION_SECTION, self._CONNECTION_PORT_OPTION, self._CONNECTION_PORT_DEFAULT))
        username = self.__get_option_from_config(config_parser, self._CONNECTION_SECTION, self._CONNECTION_USERNAME_OPTION, self._CONNECTION_USERNAME_DEFAULT)
        password = self.__get_option_from_config(config_parser, self._CONNECTION_SECTION, self._CONNECTION_PASSWORD_OPTION, self._CONNECTION_PASSWORD_DEFAULT)
        
        return ConnectionConfiguration(ipaddress, port, username, password)
        
    def save_connection_configuration(self, connection_configuration):
        self._save(connection_configuration = connection_configuration)

    def get_app_version(self):
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(self._config_filename)
        
        #Section MINISERVER
        return self.__get_option_from_config(config_parser, self._MINISERVER_SECTION, self._APPVERSION_OPTION, self._APPVERSION_DEFAULT)

    def save_app_version(self, app_version):
        self._save(app_version = app_version)
            
    def _save(self, connection_configuration = None, app_version = None):
        if(connection_configuration is None):
            connection_configuration = self.get_connection_configuration()
        if(app_version is None):
            app_version = self._APPVERSION_DEFAULT  #if configuration has changed, set appversion to default
            
        raw_config_parser = ConfigParser.RawConfigParser()        
        raw_config_parser.add_section(self._CONNECTION_SECTION)
        raw_config_parser.set(self._CONNECTION_SECTION, self._CONNECTION_IPADDRESS_OPTION, connection_configuration.ipaddress)  
        raw_config_parser.set(self._CONNECTION_SECTION, self._CONNECTION_PORT_OPTION, connection_configuration.port)  
        raw_config_parser.set(self._CONNECTION_SECTION, self._CONNECTION_USERNAME_OPTION, connection_configuration.username)  
        raw_config_parser.set(self._CONNECTION_SECTION, self._CONNECTION_PASSWORD_OPTION, connection_configuration.password) 
        
        raw_config_parser.add_section(self._MINISERVER_SECTION)
        raw_config_parser.set(self._MINISERVER_SECTION, self._APPVERSION_OPTION, app_version)
        
        with open(self._config_filename, 'w') as configfile:
            raw_config_parser.write(configfile)