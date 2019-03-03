#Imports - Enigma2
from Components.ActionMap import ActionMap
from Components.config import getConfigListEntry, ConfigInteger, ConfigIP, ConfigText, ConfigPassword 
from Components.ConfigList import ConfigListScreen 
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

#Imports - own implemented modules
from configsaver import ConfigSaver, ConnectionConfiguration
from plugin import *        
                  
class ConfigSetupScreen(ConfigListScreen, Screen):
    skin = """<screen name="Setup" position="center,center" size="560,430" title="Setup" backgroundColor="#{}">
              <ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
              <ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
              <widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" transparent="1" />
              <widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" transparent="1" />
              <widget name="config" position="5,50" size="550,325" scrollbarMode="showOnDemand" backgroundColor="#{}" backgroundColorSelected="#{}" foregroundColor="#{}"/>
            </screen>""".format(COLOR_HEX_BLACK, COLOR_HEX_DARKGREY, COLOR_HEX_GREY, COLOR_HEX_WRITING)
    
    def __init__(self, session, plugin_path, config_filename):
        self._config_saver = ConfigSaver("{}/{}".format(plugin_path, config_filename))
        self._connection_configuration = self._config_saver.get_connection_configuration()
        self._session = session
        Screen.__init__(self, self._session)
        self._list = []
        self.__ipadress_config_list_entry = ConfigIP(default = self._connection_configuration.ipaddress.split('.')) 
        self.__port_config_list_entry     = ConfigInteger(default = self._connection_configuration.port, limits = (0, 65535))
        self.__username_config_list_entry = ConfigText(default = self._connection_configuration.username, fixed_size = False, visible_width = False) #fixed_size -> input length is length of default, visible_width only one charactar visible
        self.__password_config_list_entry = ConfigPassword(default = self._connection_configuration.password, fixed_size = False, visible_width = False, censor = "*") 
        
        self._list.append(getConfigListEntry(_("IP address"), self.__ipadress_config_list_entry)) 
        self._list.append(getConfigListEntry(_("Port"),       self.__port_config_list_entry))
        self._list.append(getConfigListEntry(_("Username"),   self.__username_config_list_entry))
        self._list.append(getConfigListEntry(_("Password"),   self.__password_config_list_entry))

        ConfigListScreen.__init__(self, self._list)
        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("OK"))
        
        self["setupActions"] = ActionMap(["SetupActions"],
        {
            "save": self.save,
            "red": self.cancel,
            "cancel": self.cancel,
            "ok": self.save
        }, -2)
        
        self.onLayoutFinish.append(self.layoutFinished)
        
    def layoutFinished(self):
        self.setTitle(_("Settings"))
      
    def save(self):
        try:
            ipaddress = '.'.join(["%s" % d for d in self.__ipadress_config_list_entry.value])
            port = self.__port_config_list_entry.value
            username = self.__username_config_list_entry.value
            password = self.__password_config_list_entry.value
                     
            self._config_saver.save_connection_configuration(ConnectionConfiguration(ipaddress, port, username, password))
            self.close(False)
        except ValueError:
            self._session.open(MessageBox, _("invalid type"), type = MessageBox.TYPE_ERROR, timeout = 10, close_on_any_key = True )    
            
        return True 
        
        self.cancel()
      
    def cancel(self):
        self.close()
