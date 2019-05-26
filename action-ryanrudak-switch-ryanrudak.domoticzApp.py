#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
from hermes_python.hermes import Hermes
from hermes_python.ffi.utils import MqttOptions
from hermes_python.ontology import *
import io

CONFIGURATION_ENCODING_FORMAT = "utf-8"
CONFIG_INI = "config.ini"

class SnipsConfigParser(configparser.SafeConfigParser):
    def to_dict(self):
        return {section : {option_name : option for option_name, option in self.items(section)} for section in self.sections()}


def read_configuration_file(configuration_file):
    try:
        with io.open(configuration_file, encoding=CONFIGURATION_ENCODING_FORMAT) as f:
            conf_parser = SnipsConfigParser()
            conf_parser.readfp(f)
            return conf_parser.to_dict()
    except (IOError, configparser.Error) as e:
        return dict()

def subscribe_intent_callback(hermes, intentMessage):
    conf = read_configuration_file(CONFIG_INI)
    action_wrapper(hermes, intentMessage, conf)


def action_wrapper(hermes, intentMessage, conf):
    import io
    import requests
    import json
    import jellyfish
    
    myURL="http://"+conf.get("secret").get("hostname")+':'+conf.get("secret").get("port")+'/json.htm?type=scenes'
        response = requests.get(myURL)
        jsonresponse = response.json()#json.load(response)
        for scene in jsonresponse["result"]:
            myName=scene["Name"].encode('utf-8')
            myListSceneOrSwitch[(scene["idx"])] = {'Type':'switchscene','Name':myName}
    
    myURL="http://"+conf.get("secret").get("hostname")+':'+conf.get("secret").get("port")+'/json.htm?type=command&param=getlightswitches'
        response = requests.get(myURL)
        jsonresponse = response.json() #json.load(response)
        for sw in jsonresponse["result"]:
            myName=sw["Name"].encode('utf-8')
            myListSceneOrSwitch[(sw["idx"])] = {'Type':'switchlight','Name':myName}
    
    intentSwitchList=list()
    intentSwitchActionList=list()
    intentSwitchState='None' #by default if no action
    for (slot_value, slot) in intent.slots.items():
      print(slot_value)
      if slot_value=="action" or slot_value=="switch":
        for slot_value2 in slot.all():
          print(slot_value2.value)
    
    print("---------------------------------")
    for (slot_value, slot) in intent.slots.items():
      print(slot_value)
      if slot_value=="action":
        if slot[0].slot_value.value.value=="TurnOn":
          intentSwitchState='On'
          
        else :
          intentSwitchState='Off'
        print(intentSwitchState)
      elif slot_value=="switch":
        for slot_value2 in slot.all():
          intentSwitchList.append(slot_value2.value)
          print(slot_value2.value)
    
    if not intentSwitchState=='None':
      for mySwitch in intentSwitchList:
        intentSwitchActionList.append({'Name':mySwitch,'State':intentSwitchState})
        print(mySwitch+"------>"+intentSwitchState)
    
    result_sentence = "Schalte {} {}".format(str(action),str(house_room))
    
    current_session_id = intentMessage.session_id
    hermes.publish_end_session(current_session_id, result_sentence)
    


if __name__ == "__main__":
    mqtt_opts = MqttOptions()
    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intent("ryanrudak:switch", subscribe_intent_callback) \
         .start()
