#Imports - Enigma2
from Components.ActionMap import ActionMap 
from Screens.Screen import Screen     
from Screens.MessageBox import MessageBox

#Imports - own implemented modules
from config import ConfigSetupScreen
from app import RoomSelection
from plugin import *
    
#Constants
CONFIG_FILENAME = 'config.cfg'
    
class MiniserverSelection(Screen):
    skin = """  <screen name="MiniserverSelection" position="center,center" size="350,400" title="{}" backgroundColor="#{}">
                <eLabel backgroundColor="#{}" position="0,10" size="350,50" zPosition="1" />
                <eLabel text="{}" position="15,20" size="200,40" font="Regular; 32" backgroundColor="#{}" zPosition="3" />
                <eLabel backgroundColor="#585858" position="0,100" size="350,50" zPosition="1" />
                <eLabel text="Miniserver" position="15,110" size="200,40" font="Regular; 32" backgroundColor="#585858" zPosition="3" />
                </screen>""".format(PLUGIN_NAME, COLOR_HEX_BLACK, COLOR_HEX_GREEN, PLUGIN_NAME, COLOR_HEX_GREEN)
              
    def __init__(self, session, plugin_path):                        
        Screen.__init__(self, session)
        self._plugin_path = plugin_path
        self._session = session
        #actions          
        self["actions"] = ActionMap(['OkCancelActions',    #ok, cancel
                                     'MediaPlayerActions'  #menu
                                     ],
        {
            "ok": self.__ok,
            "cancel": self.__cancel,
            "menu": self.__configuration,  
        }, -1)
             
               
    def __ok(self):
        try:
            self.session.open(RoomSelection, self._plugin_path, CONFIG_FILENAME)  
        except:
            self.onShown.append(self._communication_error)           
            return  #continue if an exception happend
        self.__cancel()
                    
    def _communication_error(self):
        self._session.openWithCallback(self._show_with_callback, MessageBox, _("Communication") + ' ' +_("Error") + '!', type = MessageBox.TYPE_ERROR, timeout = 10, close_on_any_key = True ) 
        self.onShown.remove(self._communication_error) 
                  
    def _show_with_callback(self, value):
        self.show()
                  
    def __cancel(self):
        self.close()  

    def __configuration(self):
        self.session.open(ConfigSetupScreen, self._plugin_path, CONFIG_FILENAME)  
            