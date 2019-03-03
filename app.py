#Imports - Enigma2
from Components.ActionMap import ActionMap 
from Components.AVSwitch import AVSwitch
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend, MultiContentEntryProgress, MultiContentTemplateColor
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, eTimer, getDesktop, ePicLoad
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import fileExists
from Tools.LoadPixmap import LoadPixmap

#Imports - standard Pyhton library
import base64
import copy
import json 
import logging
import math                     
import os
import string
import urllib2

#Imports - own implemented modules
from configsaver import ConfigSaver, ConnectionConfiguration
from websocketclient import WebSocketClient, WebSocketClientException
from plugin import *

#Constants
IMAGES_FILENAME = 'images'
IMAGES_TEMP_FILENAME = '{}/temp'.format(IMAGES_FILENAME)
IMAGES_TEMP_INTERCOM_IMAGE = '{}/intercom.jpg'.format(IMAGES_TEMP_FILENAME)
STRUCTUR_FILENAME = 'LoxAPP3.json'
IMAGE_TYPE_SVG = 'svg'
IMAGE_TYPE_PNG = 'png'

CONTROL_SWITCH_STATUS_ON = 'on'
CONTROL_SWITCH_STATUS_OFF = 'off'

CONTROL_PUSHBUTTON_PULSE = 'pulse'

CONTROL_DIMMER_VALUE_MIN = 0
CONTROL_DIMMER_VALUE_MAX = 100
CONTROL_DIMMER_VALUE_STEP = 20

CONTROL_JALOUSIE_UP   = 'up'
CONTROL_JALOUSIE_DOWN = 'down'

CONTROL_UPDOWNDIGITAL_PULSEUP = 'pulseup'
CONTROL_UPDOWNDIGITAL_PULSEDOWN = 'pulsedown'

CONTROL_LEFTRIGHTDIGITAL_LEFT = 'pulseleft'
CONTROL_LEFTRIGHTDIGITAL_RIGHT = 'pulseright'

CONTROL_COLORPICKER_OFF_INDEX  = 0

ENCODING_UTF8 = 'utf8'

CONTROL_TYPE                      = 'type'
CONTROL_TYPE_SWITCH               = 'switch'
CONTROL_TYPE_PUSHBUTTON           = 'pushbutton'
CONTROL_TYPE_DIMMER               = 'dimmer'
CONTROL_TYPE_JALOUSIE             = 'jalousie'
CONTROL_TYPE_COLORPICKER          = 'colorpicker'
CONTROL_TYPE_INFO_ONLY_ANALOG     = 'infoonlyanalog'
CONTROL_TYPE_INFO_ONLY_DIGITAL    = 'infoonlydigital'
CONTROL_TYPE_FRONIUS              = 'fronius'
CONTROL_TYPE_UP_DOWN_DIGITAL      = 'updowndigital'
CONTROL_TYPE_LEFT_RIGHT_DIGITAL   = 'leftrightdigital'
CONTROL_TYPE_INTERCOM             = 'intercom'
CONTROL_TYPE_LIGHTCONTROLLER      = 'lightcontroller' 

STATUS_UPDATE_INTERVAL         = 1000 #1 Second

#Images
IMAGE_DOWN                     = 'down.png'
IMAGE_UP                       = 'up.png'
IMAGE_LEFT                     = 'left.png'
IMAGE_RIGHT                    = 'right.png'
IMAGE_PUSHBUTTON               = 'pushbutton.png'
IMAGE_FRONIUSHOME              = 'fronius_home.png'
IMAGE_FRONIUSPROD              = 'fronius_prod.png'
IMAGE_FRONIUSCONS              = 'fronius_cons.png'

class ImageCollection:
    def __init__(self):
        self._down_png = None
        self._up_png = None
        self._left_png = None
        self._right_png = None
        self._pushbutton_png = None
        self._fronius_home_png = None
        self._fronius_prod_png = None
        self._fronius_cons_png = None
    
    def _load_image(self, name):
        file_name_path = "{}/{}/{}".format(plugin_path, IMAGES_FILENAME, name)
        return LoadPixmap(file_name_path)    
                       
    def get_down_image(self):
        if(self._down_png == None):
            self._down_png = self._load_image(IMAGE_DOWN)
            
        return self._down_png   
    
    def get_up_image(self):
        if(self._up_png == None):
            self._up_png = self._load_image(IMAGE_UP)
            
        return self._up_png   

    def get_left_image(self):
        if(self._left_png == None):
            self._left_png = self._load_image(IMAGE_LEFT)
            
        return self._left_png   
        
    def get_right_image(self):
        if(self._right_png == None):
            self._right_png = self._load_image(IMAGE_RIGHT)
            
        return self._right_png
        
    def get_pushbutton_image(self):
        if(self._pushbutton_png == None):
            self._pushbutton_png = self._load_image(IMAGE_PUSHBUTTON)
            
        return self._pushbutton_png   

    def get_froniushome_image(self):
        if(self._fronius_home_png == None):
            self._fronius_home_png = self._load_image(IMAGE_FRONIUSHOME)
            
        return self._fronius_home_png   

    def get_froniusprod_image(self):
        if(self._fronius_prod_png == None):
            self._fronius_prod_png = self._load_image(IMAGE_FRONIUSPROD)
            
        return self._fronius_prod_png   

    def get_froniuscons_image(self):
        if(self._fronius_cons_png == None):
            self._fronius_cons_png = self._load_image(IMAGE_FRONIUSCONS)
            
        return self._fronius_cons_png   
        
global image_collection 
image_collection = ImageCollection()
            
            
class RoomSelectionException(Exception):
    def __init__(self, msg = ''):
        self._msg = msg
    def __str__(self):
        return repr(self._msg)
       
class RoomMenuList(MenuList):
    def __init__(self, list):
        MenuList.__init__(self, list, False, eListboxPythonMultiContent)
        self.l.setFont(0, gFont("Regular", 20))
        self.l.setItemHeight(50) 

class IntercomImage(Pixmap):
    def __init__(self):
        Pixmap.__init__(self)
        self.picload = ePicLoad()
        self.picload_conn = self.picload.PictureData.connect(self.paintIconPixmapCB)
        
    def __del__(self):        
        del self.picload    
           
    def onShow(self):
        Pixmap.onShow(self)
        sc = AVSwitch().getFramebufferScale()
        self.picload.setPara((self.instance.size().width(), self.instance.size().height(), sc[0], sc[1], 0, 0, '#00000000'))
        
    def paintIconPixmapCB(self, picInfo=None):
        ptr = self.picload.getData()
        if ptr != None:
            self.instance.setPixmap(ptr)
        
    def updateIcon(self, filename):
        self._file_name = filename
        self.picload.startDecode(self._file_name)        

class Structur:
    def __init__(self, config_json_str):
        self.__config_json = json.loads(config_json_str)
        self.__control_factory = ControlFactory()
        self._controls = self.__get_controls()
        self._cats = self.read_cats()
                    
    def get_ms_name(self):
        return self.__config_json['msInfo']['msName'].encode(ENCODING_UTF8)
      
    def get_cats(self):
        return self._cats
      
    def read_cats(self):
        cats = []
        for cats_uuid in self.__config_json['cats']:
            cat = self.__config_json['cats'][cats_uuid]
            cats.append(Cat(cat['uuid'], cat['name'].encode(ENCODING_UTF8), cat['image'], cat['defaultRating']))
                                 
        return cats
      
    def get_rooms(self):
        rooms = []
        for room_uuid in self.__config_json['rooms']:
            room = self.__config_json['rooms'][room_uuid]
            rooms.append(Room(room['uuid'], room['name'].encode(ENCODING_UTF8), room['image'], room['defaultRating'], self.__get_room_controls(room['uuid']), 
                              self.__get_room_cats(room['uuid'])))
            
        rooms = list(filter(lambda x: len(x._controls) > 0, rooms))  #remove all rooms without any control         
                    
        return sorted(rooms, key=lambda x: x._default_rating, reverse=True)  #sort rooms with according to their defaultRating 

    def __get_controls(self):
        controls = []
        for control_uuid in self.__config_json['controls']:
            control = self.__config_json['controls'][control_uuid]
            if str(control[CONTROL_TYPE]).lower() in [CONTROL_TYPE_SWITCH, CONTROL_TYPE_PUSHBUTTON, CONTROL_TYPE_DIMMER, CONTROL_TYPE_JALOUSIE, CONTROL_TYPE_INFO_ONLY_ANALOG, CONTROL_TYPE_INFO_ONLY_DIGITAL, CONTROL_TYPE_FRONIUS, CONTROL_TYPE_UP_DOWN_DIGITAL, CONTROL_TYPE_LEFT_RIGHT_DIGITAL, CONTROL_TYPE_LIGHTCONTROLLER, CONTROL_TYPE_INTERCOM]:
                if(str(control[CONTROL_TYPE]).lower() == CONTROL_TYPE_LIGHTCONTROLLER):
                     for sub_control_uuid in control['subControls']:
                        sub_control = control['subControls'][sub_control_uuid]
                        if str(sub_control[CONTROL_TYPE]).lower() in [CONTROL_TYPE_SWITCH, CONTROL_TYPE_DIMMER]:  #TODO CONTROL_TYPE_COLORPICKER
                            controls.append(self.__control_factory.get_control(sub_control, control['room'], control['cat']))
                else:
                    controls.append(self.__control_factory.get_control(control, control['room'], control['cat']))
                
        return controls 
        
    def __get_room_cats(self, room):
        cats = []
        for ca in self._cats:
            cats.append(copy.deepcopy(ca))
        
        for c in self._controls:
            if(room == c.room_uuid):
                for cat in cats:
                    if(cat.uuid == c.cat):
                        cat.add_control(c)
 
        cats = list(filter(lambda x: len(x._controls) > 0, cats))  #remove all cats without any control
        return cats
          
    def __get_room_controls(self, room):
        controls = []
        
        for c in self._controls:
            if(room == c.room_uuid):
                controls.append(c)
        
        return sorted(controls, key=lambda x: x._default_rating, reverse=True)  #sort rooms according to their defaultRating      
	
class Room:
    def __init__(self, uuid, name, image, default_rating, controls = [], cats = []):
        self.uuid = uuid
        self._name = name
        self._image = image.replace(IMAGE_TYPE_SVG, IMAGE_TYPE_PNG)  #change "svg" to "png", because Enigma2 can only deal with png or jpeg
        self._default_rating = default_rating
        self._controls = controls
        self._cats = cats

    def add_control(self, control):
        self._controls.append(control)
        
    def get_room_entry_component(self):
        image_filename = "{}/{}/{}".format(plugin_path, IMAGES_TEMP_FILENAME, self._image)
        png = LoadPixmap(image_filename)
   
        res = [()]
        res.append(MultiContentEntryText(pos=(50, 13), size=(200, 50), text=self._name, flags=RT_HALIGN_LEFT))
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (10, 5), size = (40, 40), png = png))
        return res 
        
class Component:
    def __init__(self):
        self._is_showable = False
        self._active = False

    def is_showable(self):
        return self._is_showable
               
    def show(self, screen):
        return
               
    def get_ok_command(self):
        return None 
    
    def get_left_command(self):
        return None
     
    def get_right_command(self):
        return None 
        
    def get_green_command(self):
        return None
        
    def get_red_command(self):
        return None

    def get_yellow_command(self):
        return None

    def get_blue_command(self):
        return None
        
    def update_state(self, uuid_state, value):
        return False
     
    def get_states(self):
        yield None
        
    def is_active(self):
        return self._active 
        
    def deactivate(self):
        self._active = False
        
class Control(Component):
    def __init__(self, json_control, room_uuid, cat_uuid):
        Component.__init__(self)
        self._name = json_control['name'].encode(ENCODING_UTF8)
        self._uuid_action = json_control['uuidAction']
        if(json_control.has_key('states')):
            self._states = json_control['states']
        self._default_rating = json_control['defaultRating']
        self.room_uuid = room_uuid
        
        self.cat = cat_uuid
                    
    
    def _get_command(self, value):
        return "{}/{}".format(self._uuid_action, value)  
     
    def needs_images(self):
        return False
        
    def has_secured_details(self):
        return False
    
    def set_secured_details(self, details):
        return
     
    def get_images(self):
        return None

    def _get_control_entry_component_label(self, right, name = None):
        res = [()]
        if name is None:
            name = self._name
        res.append(MultiContentEntryText(pos = (10, 13), size = (right - 50, 50), flags = RT_HALIGN_LEFT, text = name))
        return res

        
    def get_control_entry_components(self, position_value):
        yield None
                     
        
class Cat(Component):
    def __init__(self, uuid, name, image, default_rating, controls = []):
        Component.__init__(self)
        self.uuid = uuid
        self._name = name
        self._image = image.replace(IMAGE_TYPE_SVG, IMAGE_TYPE_PNG)  #change "svg" to "png", because Enigma2 can only deal with png or jpeg
        self._default_rating = default_rating
        self._controls = controls

    def add_control(self, control):
        self._controls.append(control)

    def get_components(self, control_list_left_pos, control_list_width, controllist):
        components = []
        
        controllist.append(self)
                
        image_filename = "{}/{}/{}".format(plugin_path, IMAGES_TEMP_FILENAME, self._image)
        png = LoadPixmap(image_filename)

    
        res = [()]
        res.append(MultiContentEntryText(pos = (0, 0), size = (control_list_width, 50), backcolor = int(COLOR_HEX_BLACK,16), backcolor_sel = int(COLOR_HEX_BLACK,16)))
        res.append(MultiContentEntryText(pos = (50, 13), size = (control_list_width, 50), flags = RT_HALIGN_LEFT, text = self._name, backcolor = int(COLOR_HEX_BLACK,16), backcolor_sel = int(COLOR_HEX_BLACK,16)))
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (10, 5), size = (40, 40), png = png))

        components.append(res)


        for control in self._controls:
            for component in control.get_control_entry_components(control_list_left_pos):
                controllist.append(control)
                components.append(component)
            
        return components

    def get_control_entry_components(self, position_value):
        yield None        
    
class ControlFactory:        
    def get_control(self, json_control, room_uuid, cat_uuid):     
        if(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_SWITCH):
            return Switch(json_control, room_uuid, cat_uuid)
            
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_PUSHBUTTON):
            return PushButton(json_control, room_uuid, cat_uuid)
                
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_DIMMER):
            return Dimmer(json_control, room_uuid, cat_uuid)        
                
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_JALOUSIE):
            return Jalousie(json_control, room_uuid, cat_uuid)
            
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_UP_DOWN_DIGITAL):
            return UpDownDigital(json_control, room_uuid, cat_uuid)
            
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_LEFT_RIGHT_DIGITAL):
            return LeftRightDigital(json_control, room_uuid, cat_uuid)
        
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_COLORPICKER):
            return ColorPicker(json_control, room_uuid, cat_uuid)
            
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_INFO_ONLY_ANALOG):
            return InfoOnlyAnalog(json_control, room_uuid, cat_uuid)
         
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_INFO_ONLY_DIGITAL):
            return InfoOnlyDigital(json_control, room_uuid, cat_uuid)
            
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_FRONIUS):
            return Fronius(json_control, room_uuid, cat_uuid)
            
        elif(str(json_control[CONTROL_TYPE]).lower() == CONTROL_TYPE_INTERCOM):
            return Intercom(json_control, room_uuid, cat_uuid)
        
        raise ValueError("Type is invalid")

		            
class Switch(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)
        self._status = CONTROL_SWITCH_STATUS_OFF
        self._logger = logging.getLogger('Switch')
        
    def get_ok_command(self):
        if(self._status == CONTROL_SWITCH_STATUS_OFF):
           new_status = CONTROL_SWITCH_STATUS_ON
        else:   
           new_status = CONTROL_SWITCH_STATUS_OFF        
           
        return self._get_command(new_status)
        
    def get_control_entry_components(self, position_value):    
        res = self._get_control_entry_component_label(position_value)
        
        left_position = position_value + 25
        
        if(self._status == CONTROL_SWITCH_STATUS_OFF):
            backgroundcolor = COLOR_HEX_WHITE
            frontcolor = COLOR_HEX_DARKGREY
            left = left_position + 6
        else:
            backgroundcolor = COLOR_HEX_GREEN
            frontcolor = COLOR_HEX_WHITE
            left = left_position + 17
        
        res.append(MultiContentEntryText(pos = (left_position, 5), size = (40, 40), backcolor = int(backgroundcolor,16), backcolor_sel = int(backgroundcolor,16)))        
        res.append(MultiContentEntryText(pos = (left, 11), size = (17, 28), backcolor = int(frontcolor,16), backcolor_sel = int(frontcolor,16)))        
        
        yield res
        
    def update_state(self, uuid_state, value):
        if(self._states['active'] == uuid_state):
           if((value == 0.0) and (self._status != CONTROL_SWITCH_STATUS_OFF)):
                self._status = CONTROL_SWITCH_STATUS_OFF   
                return True
                
           elif((value != 0.0) and (self._status != CONTROL_SWITCH_STATUS_ON)):
                self._status = CONTROL_SWITCH_STATUS_ON
                return True
                   
        return False

    def get_states(self):
        yield self._states['active']
        
class PushButton(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)
        
    def get_ok_command(self):    
        return self._get_command(CONTROL_PUSHBUTTON_PULSE)
        
    def get_control_entry_components(self, position_value):
        png = image_collection.get_pushbutton_image()
    
        res = self._get_control_entry_component_label(position_value)
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value+25, 5), size = (40, 40), png = png))
        yield res 
        
class Dimmer(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)
        self._value = CONTROL_DIMMER_VALUE_MIN  #valid values from 0 .. 100
                
    def get_ok_command(self):
        if(self._value):
            new_value = CONTROL_DIMMER_VALUE_MIN
        else:
            new_value = CONTROL_DIMMER_VALUE_MAX

        return self._get_command(new_value)

    def get_left_command(self):
        if(self._value == CONTROL_DIMMER_VALUE_MIN):
            return None
        
        if(self._value < CONTROL_DIMMER_VALUE_STEP):
            new_value = CONTROL_DIMMER_VALUE_MIN
        else:
            new_value = self._value - CONTROL_DIMMER_VALUE_STEP
                               
        return self._get_command(new_value)
     
    def get_right_command(self): 
        if(self._value > CONTROL_DIMMER_VALUE_MAX):
            return None
        
        new_value = self._value + CONTROL_DIMMER_VALUE_STEP
        
        if(new_value > CONTROL_DIMMER_VALUE_MAX):
            new_value = CONTROL_DIMMER_VALUE_MAX
        
        return self._get_command(new_value)
        
    def get_control_entry_components(self, position_value):
        res = self._get_control_entry_component_label(position_value)
        res.append(MultiContentEntryProgress(pos = (position_value-15, 5), size = (120, 40), percent = self._value))  
        yield res
        
    def update_state(self, uuid_state, value):
        if(self._states['position'] == uuid_state):
            
            if(self._value != value):
                self._value = value;
                return True
        
        return False 
        
    def get_states(self):
        yield self._states['position']    
        
class Jalousie(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)
        self._position = 0.0;
    
    def get_green_command(self):
        return self._get_command(CONTROL_JALOUSIE_UP)          
        
    def get_red_command(self):
        return self._get_command(CONTROL_JALOUSIE_DOWN)              
    
    def get_control_entry_components(self, position_value):
        up_png = image_collection.get_up_image()
        down_png = image_collection.get_down_image()
        
        res = self._get_control_entry_component_label(position_value)
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value-20, 5), size = (40, 40), png = up_png))         

        top = math.ceil(36 * self._position)
        height = 40
        left = position_value + 23
        res.append(MultiContentEntryText(pos = (left, 5), size = (40, height), backcolor = int(COLOR_HEX_BLACK,16), backcolor_sel = int(COLOR_HEX_BLACK,16)))        
        res.append(MultiContentEntryText(pos = (left + 1, 6), size = (38, 38), backcolor = int(COLOR_HEX_WHITE,16), backcolor_sel = int(COLOR_HEX_WHITE,16)))        
        res.append(MultiContentEntryText(pos = (left + 2, 7), size = (36, 36), backcolor = int(COLOR_HEX_BLACK,16), backcolor_sel = int(COLOR_HEX_BLACK,16)))        
        res.append(MultiContentEntryText(pos = (left + 2, 7 + top), size = (36, height - 4 - top), backcolor = int(COLOR_HEX_DARKGREY,16), backcolor_sel = int(COLOR_HEX_DARKGREY,16)))        
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value+70, 5), size = (40, 40), png = down_png))         

        yield res
        
    def update_state(self, uuid_state, value):
        if(self._states['position'] == uuid_state):
            
            if(self._position != value):
                self._position = value;
                return True
        
        return False 
        
    def get_states(self):
        yield self._states['position']    
        

class UpDownDigital(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)

    def get_green_command(self):
        return self._get_command(CONTROL_UPDOWNDIGITAL_PULSEUP)          
        
    def get_red_command(self):
        return self._get_command(CONTROL_UPDOWNDIGITAL_PULSEDOWN) 
            
    def get_control_entry_components(self, position_value):       
        up_png = image_collection.get_up_image()
        down_png = image_collection.get_down_image()
        
        res = self._get_control_entry_component_label(position_value)
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value, 5), size = (40, 40), png = up_png))         
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value+50, 5), size = (40, 40), png = down_png))                 
        yield res

class LeftRightDigital(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)

    def get_green_command(self):
        return self._get_command(CONTROL_LEFTRIGHTDIGITAL_RIGHT)  #Bug left and right seems to be exchanged      
        
    def get_red_command(self):
        return self._get_command(CONTROL_LEFTRIGHTDIGITAL_LEFT)  #Bug left and right seems to be exchanged
        
    def get_control_entry_components(self, position_value):       
        left_png = image_collection.get_left_image()
        right_png = image_collection.get_right_image()
        
        res = self._get_control_entry_component_label(position_value)
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value, 5), size = (40, 40), png = left_png))         
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value+50, 5), size = (40, 40), png = right_png))                 
        yield res
        
class ColorPicker(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)
        self._color_index = CONTROL_COLORPICKER_OFF_INDEX 
        self._colorlist = ['000000000', '255000000', '255255000','000255000', '000000255', '255000255', '000255255']
        self._color = self._colorlist[CONTROL_COLORPICKER_OFF_INDEX]
              
    def get_red_command(self):
        self._color_index = CONTROL_COLORPICKER_OFF_INDEX
        return self._get_command('setfav/color/{}#'.format(self._colorlist[self._color_index])) 
        
    def get_left_command(self):
        if(self._color_index == CONTROL_COLORPICKER_OFF_INDEX):
            return None
       
        self._color_index -= 1;
       
        return self._get_command(self._colorlist[self._color_index])
     
    def get_right_command(self): 
        if(self._color_index == len(self._colorlist) -1):
            return None
        
        self._color_index += 1;
        
        return self._get_command(self._colorlist[self._color_index])
                
    def get_control_entry_components(self, position_value): 
        res = self._get_control_entry_component_label(position_value)
        
        colorhex = "%02X%02X%02X" % (int(self._color[6:9]), int(self._color[3:6]), int(self._color[0:3]))
        res.append(MultiContentEntryText(pos = (position_value-15, 5), size = (120, 40), backcolor = int(colorhex,16), backcolor_sel = int(colorhex,16)))        
        yield res
        
    def update_state(self, uuid_state, value): 
        if(uuid_state == self._states['color']):
            if(self._color != str(value)[:str(value).find('.')].zfill(9)):
                self._color = str(value)[:str(value).find('.')].zfill(9)               
                return True
        
        return False 
        
    def get_states(self):
        yield self._states['color']        
        
class InfoOnlyAnalog(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)
        self._value = None
        self._format = json_control['details']['format'].encode(ENCODING_UTF8)
                              
    def get_control_entry_components(self, position_value = 0): 
        if(self._value is not None):
            text = str(self._format) % self._value 
        else:
            text = ''

        res = self._get_control_entry_component_label(position_value)
        res.append(MultiContentEntryText(pos = (position_value, 13), size = (120, 40), flags = RT_HALIGN_LEFT, text = text))        
        yield res
        
    def update_state(self, uuid_state, value): 
        if(uuid_state == self._states['value']):
            if(self._value != value):
                self._value = value
                return True
        
        return False
        
    def get_states(self):
        yield self._states['value']
        
class InfoOnlyDigital(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)
        self._value = None
        self._text = None
        self._color = None
        self._image = None
        
        if(json_control['details']).has_key('text'):
            self._text = json_control['details']['text']  
            self._color = json_control['details']['color']
            
        elif(json_control['details']).has_key('image'):
            self._image = json_control['details']['image']
            
    def get_control_entry_components(self, position_value): 
        res = self._get_control_entry_component_label(position_value)

        if(self._text is not None):
            if(self._value == 0.0):
                text = str(self._text['off'])
                color =  self._color['off'][1:] 
            else:
                text = str(self._text['on'])
                color = self._color['on'][1:] 
            
            res.append(MultiContentEntryText(pos = (position_value, 13), size = (120, 40), flags = RT_HALIGN_LEFT, text = text, color = int(color,16), color_sel = int(color,16)))        
        
        elif(self._image is not None):
            if(self._value == 0.0):
                file_name_path = "{}/{}/{}.{}".format(plugin_path, IMAGES_TEMP_FILENAME, self._image['off'], IMAGE_TYPE_PNG)
            else:
                file_name_path = "{}/{}/{}.{}".format(plugin_path, IMAGES_TEMP_FILENAME, self._image['on'], IMAGE_TYPE_PNG)
              
            png = LoadPixmap(file_name_path)
        
            res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value+28, 5), size = (40, 40), png = png))
        yield res
        
    def needs_images(self):
        return (self._image is not None)
     
    def get_images(self):
        yield "{}.{}".format(self._image['on'], IMAGE_TYPE_PNG)
        yield "{}.{}".format(self._image['off'], IMAGE_TYPE_PNG)
        
    def update_state(self, uuid_state, value): 
        if(uuid_state == self._states['active']):
            if(self._value != value):
                self._value = value
                return True
                
        return False
        
    def get_states(self):
        yield self._states['active']
        
class Fronius(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)
        #prod_curr
        self._uuid_prod_curr = None
        self._name_prod_curr = None
        self._format_prod_curr = None
        self._prod_curr = None
        #cons_curr
        self._uuid_cons_curr = None
        self._name_cons_curr = None
        self._format_cons_curr = None
        self._cons_curr = None
        #prod_curr_day
        self._uuid_prod_curr_day = None
        self._name_prod_curr_day = None
        self._prod_curr_day = None
        #cons_curr_day
        self._uuid_cons_curr_day = None
        self._name_cons_curr_day = None
        self._cons_curr_day = None
        #prod_curr_month
        self._uuid_prod_curr_month = None
        self._name_prod_curr_month = None
        self._prod_curr_month = None
        #prod_curr_year
        self._uuid_prod_curr_year = None
        self._name_prod_curr_year = None
        self._prod_curr_year = None
        #prod_total
        self._uuid_prod_total = None
        self._name_prod_total = None
        self._prod_total = None
        
        self._uuid_prod_curr = json_control['states']['prodCurr']
        self._uuid_cons_curr = json_control['states']['consCurr']
        self._uuid_prod_curr_day = json_control['states']['prodCurrDay']
        self._uuid_cons_curr_day = json_control['states']['consCurrDay']
        self._uuid_prod_curr_month = json_control['states']['prodCurrMonth']
        self._uuid_prod_curr_year = json_control['states']['prodCurrYear']
        self._uuid_prod_total = json_control['states']['prodTotal']


        for option in json_control['statistic']['outputs']:
            if option['uuid'] == self._uuid_prod_curr:
                self._format_prod_curr = option ['format'].encode(ENCODING_UTF8)
                self._name_prod_curr = option['name'].encode(ENCODING_UTF8) + ' aktuell'
                self._name_prod_curr_day = option['name'].encode(ENCODING_UTF8) + ' heute'
                self._name_prod_curr_month = option['name'].encode(ENCODING_UTF8) + ' aktuelles Monat'
                self._name_prod_curr_year = option['name'].encode(ENCODING_UTF8) + ' aktuelles Jahr'
                self._name_prod_total = option['name'].encode(ENCODING_UTF8) + ' gesamt'
                
            elif option['uuid'] == self._uuid_cons_curr:
                self._format_cons_curr = option ['format'].encode(ENCODING_UTF8)
                self._name_cons_curr = option['name'].encode(ENCODING_UTF8) + ' aktuell'
                self._name_cons_curr_day = option['name'].encode(ENCODING_UTF8) + ' heute'
                                             
    def _get_control_entry_component(self, position_value, name, value, format):
        value_str = ''
        
        if(value is not None):
            value_str = str(format) % value 
              
        res = self._get_control_entry_component_label(position_value, name)
        res.append(MultiContentEntryText(pos = (position_value, 13), size = (120, 40), flags = RT_HALIGN_LEFT, text = value_str))        
               
        return res
    
    def get_control_entry_components(self, position_value):
        #Current
        froniushome_png = image_collection.get_froniushome_image()
        froniusprod_png = image_collection.get_froniusprod_image()
        froniuscons_png = image_collection.get_froniuscons_image()

        cons_curr_val = 0
        cons_curr_str = ''
        prod_curr_val = 0
        prod_curr_str = ''
        cons_str = ''
        cons_val = ''
        prod_str = ''
        
        if(self._cons_curr is not None):
            cons_curr_val = self._cons_curr
            cons_curr_str = str(self._format_cons_curr) % self._cons_curr

        if(self._prod_curr is not None):
            prod_curr_val = self._prod_curr
            prod_curr_str = str(self._format_prod_curr) % self._prod_curr
            if(prod_curr_val > 0):
                prod_str = '< {} <'.format(prod_curr_str)

        if(self._cons_curr is not None) and (self._prod_curr is not None):
            cons_val = self._cons_curr - self._prod_curr
            if(cons_val < 0):
                cons_val *= -1
            cons_val = str(self._format_prod_curr) % cons_val
            
        if(cons_curr_val < prod_curr_val):
            cons_str = '< {} <'.format(cons_val)
        elif(cons_curr_val > prod_curr_val):
            cons_str = '> {} >'.format(cons_val)
            
                    
        res = self._get_control_entry_component_label(position_value, 'Leistung aktuell')
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value, 5), size = (40, 40), png = froniuscons_png))         
        res.append(MultiContentEntryText(pos = (position_value + 45, 13), size = (130, 40), flags = RT_HALIGN_LEFT, text = cons_str))       
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value + 175, 5), size = (40, 40), png = froniushome_png))         
        res.append(MultiContentEntryText(pos = (position_value + 225, 13), size = (130, 40), flags = RT_HALIGN_LEFT, text = prod_str))
        res.append(MultiContentEntryPixmapAlphaBlend(pos = (position_value + 350, 5), size = (40, 40), png = froniusprod_png))         
        yield res

        yield self._get_control_entry_component(position_value, self._name_cons_curr, self._cons_curr, self._format_cons_curr)        
        yield self._get_control_entry_component(position_value, self._name_prod_curr_day, self._prod_curr_day, self._format_prod_curr)
        yield self._get_control_entry_component(position_value, self._name_prod_curr_month, self._prod_curr_month, self._format_prod_curr)
        yield self._get_control_entry_component(position_value, self._name_prod_curr_year, self._prod_curr_year, self._format_prod_curr)
        yield self._get_control_entry_component(position_value, self._name_prod_total, self._prod_total, self._format_prod_curr)        
        yield self._get_control_entry_component(position_value, self._name_cons_curr_day, self._cons_curr_day, self._format_cons_curr) 
                
    def update_state(self, uuid_state, value): 
        if(uuid_state == self._uuid_prod_curr):
            if(self._prod_curr != value):
                self._prod_curr = value
                return True
            return False
        elif(uuid_state == self._uuid_prod_curr_day):
            if(self._prod_curr_day != value):
                self._prod_curr_day = value
                return True
            return False
        elif(uuid_state == self._uuid_prod_curr_month):
            if(self._prod_curr_month != value):
                self._prod_curr_month = value
                return True
            return False
        elif(uuid_state == self._uuid_prod_curr_year):
            if(self._prod_curr_year != value):
                self._prod_curr_year = value
                return True
            return False
        elif(uuid_state == self._uuid_prod_total):
            if(self._prod_total != value):
                self._prod_total = value
                return True
            return False
        elif(uuid_state == self._uuid_cons_curr):
            if(self._cons_curr != value):
                self._cons_curr = value
                return True
            return False
        elif(uuid_state == self._uuid_cons_curr_day):
            if(self._cons_curr_day != value):
                self._cons_curr_day = value
                return True
            return False
        
        return False
    
    def get_states(self):
        yield self._uuid_prod_curr
        yield self._uuid_prod_curr_day
        yield self._uuid_prod_curr_month
        yield self._uuid_prod_curr_year
        yield self._uuid_prod_total
        yield self._uuid_cons_curr
        yield self._uuid_cons_curr_day
        
        
class Intercom(Control):
    def __init__(self, json_control, room_uuid, cat_uuid):     
        Control.__init__(self, json_control, room_uuid, cat_uuid)
        self._alert_image = None
        self._user = ''
        self._pass = ''
        self._screen_control = None
        self._is_showable = True
        self._image_filename = "{}/{}".format(plugin_path, IMAGES_TEMP_INTERCOM_IMAGE)   
        self._timer_active = False
        self._logger = logging.getLogger('Intercom')
        
    def get_control_entry_components(self, position_value):   
        res = self._get_control_entry_component_label(position_value)
        yield res
        
    def has_secured_details(self):
        return True
        
    def set_secured_details(self, details):
        details_json = json.loads(details)

        if(details_json['videoInfo']).has_key('alertImage'):
            self._alert_image = details_json['videoInfo']['alertImage']          
        
        if(details_json['videoInfo']).has_key('user'):
            self._user = details_json['videoInfo']['user']
        
        if(details_json['videoInfo']).has_key('pass'):
            self._pass = details_json['videoInfo']['pass']
            
    def show(self, screen):  
        if(self._active == True):
            return
            
        if(self._alert_image is None):
            return
 
        self._screen_control = screen.get_intercom_screen_control()
        self._screen_control.show()
            
        self._active = True
        self._timer = eTimer()   
        self._timer_conn = self._timer.timeout.connect(self.on_update)        
        self._timer.start(300, False)
        self._timer_active = True
        
    def _cancel(self):
        if(self._timer_active):
            self._timer.stop()
            self._timer_active = False
        
    def deactivate(self):
        self._cancel()
        self._active = False
        self._screen_control.hide()
        
    def on_update(self):
        try:
            request = urllib2.Request(self._alert_image)
            
            if (self._user != '') and (self._pass != ''):
                base64string = base64.encodestring('%s:%s' % (self_user, self._pass)).replace('\n', '')
                request.add_header("Authorization", "Basic %s" % base64string)
                self._logger.debug('Basic auth: {}'.format(base64string))


            #resp = urllib2.urlopen(self._alert_image, timeout=1).read()       
            resp = urllib2.urlopen(request, timeout=1).read()

            myfile = open(self._image_filename, 'wb')
            print >> myfile, resp
            myfile.close()
            self._screen_control.updateIcon(self._image_filename)
        except:
            self._cancel()
            return
            
class Miniserver:
    def __init__(self, webSocketClient, config):
        self._webSocketClient = webSocketClient
        self._config = config
        self._states = dict() 
        
        #check if local version of structur_file is up to date
        current_app_version = self._webSocketClient.get_app_version()
        if (self._exists_structur_file() == False) or (current_app_version != self._config.get_app_version()):
            self._update_structur_file()
            
        self._structur = Structur(self._read_structur_file())
                
        self.ms_name = self._structur.get_ms_name() 
        self.rooms = self._structur.get_rooms()
        self.cats = self._structur.get_cats()
        
        #register all controls for status update
        for control in self._structur._controls:
            for state in control.get_states():
                if state is not None:
                    self._states[str(state)] = control
        
        if current_app_version != self._config.get_app_version():
            self._get_room_images()
            self._get_cat_images()
            self._get_control_images()
            self._config.save_app_version(current_app_version)
            
        #get secured details
        self._get_control_secured_details()
            
    def _update_structur_file(self):
        binary = self._webSocketClient.get_structure_file()
        structure_filename = "{}/{}".format(plugin_path, STRUCTUR_FILENAME)
        with open(structure_filename, "wb") as file:
            file.write(binary)
            
    def _read_structur_file(self):
        structure_filename = "{}/{}".format(plugin_path, STRUCTUR_FILENAME)
        with open(structure_filename, "r") as file:
            binary = file.read()
        return binary.decode(ENCODING_UTF8)
        
    def _exists_structur_file(self):
        structure_filename = "{}/{}".format(plugin_path, STRUCTUR_FILENAME)
        return fileExists(structure_filename)
        
    def _get_room_images(self):
        for room in self.rooms:
            self._get_image(room._image)

    def _get_cat_images(self):
        for cat in self.cats:
            self._get_image(cat._image)
            
    def _get_control_images(self):
        for room in self.rooms:
            for control in room._controls:
                if(control.needs_images()):
                    for image in control.get_images():
                        self._get_image(image)
                
    def _get_image(self, image_name):
        image_filename = "{}/{}/{}".format(plugin_path, IMAGES_TEMP_FILENAME, image_name)
        
        #get image only if it does not exist
        if os.path.isfile(image_filename):
            return
        
        binary = self._webSocketClient.get_image(image_name)
        with open(image_filename, "wb") as file:
            file.write(binary)    
    
    def _get_control_secured_details(self):
        for room in self.rooms:
            for control in room._controls:
                if(control.has_secured_details()):
                    control.set_secured_details(self._webSocketClient.get_secured_details(control._uuid_action))
                   
    def send_comand(self, command):
        self._webSocketClient.send_command(command)
            
class RoomSelection(Screen):
    scren_size_width = getDesktop(0).size().width()
    scren_size_height = getDesktop(0).size().height()

    caption_panel_position_x = 0
    caption_panel_position_y =  scren_size_height / 100
    caption_panel_position_witdh = scren_size_width
    caption_panel_position_height = scren_size_height / 10   
   
    caption_panel_separator_width = caption_panel_position_y
    list_boarder = scren_size_width / 25
    
    room_list_position_x = list_boarder
    room_list_separator_width = caption_panel_separator_width
    room_list_position_y = caption_panel_position_y + caption_panel_position_height + list_boarder;
    room_list_position_width = (scren_size_width - 2 * list_boarder) / 3 - room_list_separator_width
    room_list_position_height = scren_size_height - room_list_position_y - list_boarder 
    
    control_list_position_y = room_list_position_y
    control_list_position_x = room_list_position_x + room_list_position_width + room_list_separator_width
    global control_list_width
    control_list_width = (scren_size_width - 2 * list_boarder) / 3 * 2
    control_list_height = room_list_position_height
    global control_list_position_value
    control_list_position_value = control_list_width / 2      
    
    caption_panel_separator_position_x = room_list_position_x + room_list_position_width 
    caption_panel_separator_width = room_list_separator_width
    
    ms_name_position_x = scren_size_width / 50 + 10
    ms_name_position_y = caption_panel_position_y
    ms_name_width = caption_panel_separator_position_x - ms_name_position_x
    ms_name_height = caption_panel_position_height
    ms_name_font_size = ms_name_height / 3 * 2
    
    room_name_position_x = caption_panel_separator_position_x + caption_panel_separator_width + 10
    room_name_position_y = ms_name_position_y
    room_name_width = scren_size_width - room_name_position_x - list_boarder
    room_name_height = ms_name_height 
    room_name_font_size = ms_name_font_size
    
    
    skin = """  <screen name="RoomSelection" position="center,center" size="{},{}" backgroundColor="#{}">
                <eLabel backgroundColor="#{}" position="{},{}" size="{},{}" zPosition="1" />
                <eLabel backgroundColor="#{}" position="{},{}" size="{}, {}" zPosition="2" />
                <widget name="ms_name" position="{},{}" size="{},{}" font="Regular; {}" backgroundColor="#{}" zPosition="3" />
                <widget name="roomname" position="{},{}" size="{},{}" font="Regular; {}" backgroundColor="#{}" zPosition="3" />
                <widget name="room_list" position="{},{}" size="{},{}" scrollbarMode="showNever" backgroundColor="#{}" backgroundColorSelected="#{}" foregroundColor="#{}" />
                <widget name="control_list" position="{},{}" size="{},{}" scrollbarMode="showNever" backgroundColor="#{}" backgroundColorSelected="#{}" foregroundColor="#{}" /> 
                <widget name="control_intercom" position="{},{}" zPosition="1" size="{},{}" alphatest="on" /> 
                </screen>""".format(scren_size_width, scren_size_height, COLOR_HEX_BLACK, 
                                    COLOR_HEX_GREEN, caption_panel_position_x, caption_panel_position_y, caption_panel_position_witdh, caption_panel_position_height,
                                    COLOR_HEX_BLACK, caption_panel_separator_position_x, caption_panel_position_y, caption_panel_separator_width, caption_panel_position_height,
                                    ms_name_position_x, ms_name_position_y, ms_name_width, ms_name_height, ms_name_font_size, COLOR_HEX_GREEN,
                                    room_name_position_x, room_name_position_y, room_name_width,room_name_height, room_name_font_size, COLOR_HEX_GREEN,
                                    room_list_position_x, room_list_position_y, room_list_position_width, room_list_position_height, COLOR_HEX_DARKGREY, COLOR_HEX_GREY, COLOR_HEX_WRITING,
                                    control_list_position_x, control_list_position_y, control_list_width, control_list_height, COLOR_HEX_DARKGREY, COLOR_HEX_GREY, COLOR_HEX_WRITING,
                                    control_list_position_x, control_list_position_y, control_list_width, control_list_height,)
              
    def __init__(self, session, path, config_filename):
        #Constants
        self.__ROOM_LIST    = 'room_list'
        self.__CONTROL_LIST = 'control_list'
        
        Screen.__init__(self, session)     
        self._session = session
        self._logger = logging.getLogger('RoomSelection')
        self._logger.debug('Start initialisation')
        
        self.__room_list = []
        self[self.__ROOM_LIST] = RoomMenuList([])
        self[self.__ROOM_LIST].l.setList(self.__room_list)
        self.__control_list = []
        self[self.__CONTROL_LIST] = RoomMenuList([])
        self.controllist = []
        self.selectedList = self.__ROOM_LIST 
        #label msname
        self["ms_name"] = Label('')
        #label roomname
        self["roomname"] = Label('')
        self["roomname"].hide()
        self["control_intercom"] = IntercomImage()
        self["control_intercom"].hide()
        self._webSocketClient = None
        self._config_path_filename = "{}/{}".format(path, config_filename) 
                
        global plugin_path
        plugin_path = path
                        
        #actions          
        self["actions"] = ActionMap(['OkCancelActions',          #ok, cancel
                                     'WizardActions',            #down,left, right, up     
                                     'ColorActions',             #red, green, blue, yellow
                                     'ChannelSelectBaseActions'  #pageup, pagedown
                                     ],
        {
            "ok": self.__ok,
            "cancel": self.__cancel,
            "up": self.__up,            
		    "down": self.__down,
            "green": self.__green,
            "red": self.__red, 
            "blue": self.__blue,
            "yellow": self.__yellow,
            "right": self.__right,
            "left": self.__left,
            "nextBouquet": self.__pageup,
            "prevBouquet": self.__pagedown
        }, -1)
        
        self.onShown.append(self.__init)
      
    def __init(self):
        self._timer = eTimer()            
        self._timer_conn = self._timer.timeout.connect(self.on_update)
               
        try:
            connection_configuration = ConfigSaver(self._config_path_filename).get_connection_configuration()
            self._webSocketClient = WebSocketClient(connection_configuration, self.on_status_update) 
            self.__miniserver = Miniserver(webSocketClient = self._webSocketClient, 
                                   config = ConfigSaver(self._config_path_filename));
        except WebSocketClientException:
            self._communication_error()  
            return      
        
        #label msname
        self["ms_name"].setText(self.__miniserver.ms_name)
        
        #list of rooms
        for room in self.__miniserver.rooms:
            self.__room_list.append(room.get_room_entry_component())
        self[self.__ROOM_LIST].l.setList(self.__room_list)
        self[self.__ROOM_LIST].onSelectionChanged.append(self._room_selection_changed)
        
        #list of controls
        self[self.__CONTROL_LIST].l.setList(self.__control_list)
                
        self.__set_room_list_enabled()
        self.__update_room()
        
        self._logger.debug('End initialisation')
        
        self._logger.debug('Enable statusupdate')
        #activate statusupdate
        try:
            self._webSocketClient.enable_status_update()
            self._timer.start(STATUS_UPDATE_INTERVAL, False) 
        except WebSocketClientException:
            self._communication_error()           
                
    def _communication_error(self):
        self.__close()
        raise RoomSelectionException('Communication Error!')
        
    def on_update(self):
        try:
            self._webSocketClient.execute()        
        except WebSocketClientException:
            self._communication_error()  
       
    def __up(self):        
        self[self.selectedList].up()
               
    def __down(self):     	
        self[self.selectedList].down()
        
    def __pageup(self):        
        self[self.selectedList].pageUp()
               
    def __pagedown(self):     	
        self[self.selectedList].pageDown()
        
    def _get_selected_control(self):
        control_index = self[self.__CONTROL_LIST].getSelectionIndex()
        return self.controllist[control_index]
        
    def __right(self):
        if self.selectedList == self.__CONTROL_LIST:
            command = self._get_selected_control().get_right_command()
            if(command is not None):
                self.__miniserver.send_comand(command)
                                
    def __left(self):
        if self.selectedList == self.__CONTROL_LIST:
            command = self._get_selected_control().get_left_command()
            if(command is not None):
                self.__miniserver.send_comand(command)
                                
    def __green(self):
        if self.selectedList == self.__CONTROL_LIST:
            command = self._get_selected_control().get_green_command()
            if(command is not None):
                self.__miniserver.send_comand(command)
                               
    def __red(self):
        if self.selectedList == self.__CONTROL_LIST:
            command = self._get_selected_control().get_red_command()
            if(command is not None):
                self.__miniserver.send_comand(command)

    def __yellow(self):
        if self.selectedList == self.__CONTROL_LIST:
            command = self._get_selected_control().get_yellow_command()
            if(command is not None):
                self.__miniserver.send_comand(command)
                
    def __blue(self):
        if self.selectedList == self.__CONTROL_LIST:
            command = self._get_selected_control().get_blue_command()
            if(command is not None):
                self.__miniserver.send_comand(command)
                
    def __set_control_list_enabled(self):
        self[self.__CONTROL_LIST].selectionEnabled(1)
        self[self.__ROOM_LIST].selectionEnabled(0)
        self.selectedList = self.__CONTROL_LIST
                
    def __set_room_list_enabled(self):
        self[self.__CONTROL_LIST].selectionEnabled(0)
        self[self.__ROOM_LIST].selectionEnabled(1)
        self.selectedList = self.__ROOM_LIST
                
    def __ok(self):
        if self.selectedList == self.__ROOM_LIST:
            self.__set_control_list_enabled()
        else:
            control = self._get_selected_control()
          
            if(control.is_showable()):
                self[self.__CONTROL_LIST].hide()
                control.show(self)
            else:
                command = control.get_ok_command()
                if(command is not None):
                    self.__miniserver.send_comand(command)
                                    
    def __cancel(self):
        if self.selectedList == self.__CONTROL_LIST:            
            if(self._get_selected_control().is_active() == True):
                self._get_selected_control().deactivate()    
                self[self.__CONTROL_LIST].show()
            else:
                self[self.__CONTROL_LIST].show()
                self.__set_room_list_enabled()
        else:
            self.__close()
              
    def __close(self):
        self._timer.stop()
        if(self._webSocketClient is not None):
            self._webSocketClient.close()
        self.close()    
                        
    def _room_selection_changed(self):
        self.__update_room()
            
    def __set_room_name(self, name):
        if(len(name) == 0):
            self["roomname"].setText('')
            self["roomname"].hide()
        else:
            self["roomname"].setText(name)
            self["roomname"].show()
            
    def __update_room(self):
        room_index = self[self.__ROOM_LIST].getSelectionIndex()        
        self.__set_room_name(self.__miniserver.rooms[room_index]._name)
        self.__control_list = []
        
        self.controllist = []
        
        for cat in self.__miniserver.rooms[room_index]._cats:          
            for comp in cat.get_components(control_list_position_value, control_list_width, self.controllist):
                self.__control_list.append(comp)
                        
        self[self.__CONTROL_LIST].l.setList(self.__control_list)     
        
        
    def on_status_update(self, uuid_state, value):
        if(self.__miniserver._states.has_key(str(uuid_state))):
            status_changed = self.__miniserver._states[str(uuid_state)].update_state(uuid_state, value)
                        
            #Update room only if status changed and room is selected
            if((status_changed == True) and (self.__miniserver._states[str(uuid_state)].room_uuid == self.__miniserver.rooms[self[self.__ROOM_LIST].getSelectionIndex()].uuid)):
                self.__update_room()
                  
    def get_intercom_screen_control(self):
        return self["control_intercom"];
               