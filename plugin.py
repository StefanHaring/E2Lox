#Global constants
PLUGIN_NAME = 'E2Lox'

#Colors
COLOR_HEX_BLACK                = "000000"
COLOR_HEX_WHITE                = "FFFFFF"
COLOR_HEX_GREEN                = "83B817"
COLOR_HEX_GREY                 = "424242"  
COLOR_HEX_DARKGREY             = "303030"  
COLOR_HEX_WRITING              = "B3C1C1"

#Imports - Enigma2
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists

#Imports - standard Python library
import logging                     #Logging
import requests

#Imports - own implemented modules
from miniserverselection import MiniserverSelection
import app
import configsaver
import websocketclient

#Constants
LOGFILE_NAME = 'App.log'
               
def main(session, **kwargs):
    reload(app)
    reload(configsaver)
    reload(websocketclient)
    try:
        logging.basicConfig(filename = '{}/{}'.format(plugin_path, LOGFILE_NAME),
                            filemode = 'w', 
                            format='%(asctime)s %(message)s',
                            level = logging.DEBUG)
        session.open(MiniserverSelection, plugin_path)  
    except:
        import traceback
        traceback.print_exc()
     
def menu(menuid, **kwargs):
    if menuid != "mainmenu": 
        return [ ]
        
    return [(PLUGIN_NAME, main, PLUGIN_NAME, None)]
                
def Plugins(path, **kwargs):
    global plugin_path
    plugin_path = path
    return [PluginDescriptor(name=PLUGIN_NAME, description='control your home', where=[PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=main), 
            PluginDescriptor(name=PLUGIN_NAME, description='control your home', where=[PluginDescriptor.WHERE_MENU], fnc=menu),
            PluginDescriptor(name=PLUGIN_NAME, description='control your home', where=[PluginDescriptor.WHERE_PLUGINMENU], fnc=main)]