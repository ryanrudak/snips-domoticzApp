#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
from hermes_python.hermes import Hermes
from hermes_python.ffi.utils import MqttOptions
from hermes_python.ontology import *
import io
import requests
import json
import jellyfish

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


def getSceneNames(conf,myListSceneOrSwitch):
    myURL="http://"+conf.get("secret").get("hostname")+':'+conf.get("secret").get("port")+'/json.htm?type=scenes'
    response = requests.get(myURL)
    jsonresponse = response.json()#json.load(response)
    for scene in jsonresponse["result"]:
        myName=scene["Name"].encode('utf-8')
        myListSceneOrSwitch[(scene["idx"])] = {'Type':'switchscene','Name':myName}
    print('---------SceneName----------')
    return myListSceneOrSwitch

def getSwitchNames(conf,myListSceneOrSwitch):
    myURL="http://"+conf.get("secret").get("hostname")+':'+conf.get("secret").get("port")+'/json.htm?type=command&param=getlightswitches'
    response = requests.get(myURL)
    jsonresponse = response.json() #json.load(response)
    for sw in jsonresponse["result"]:
        myName=sw["Name"].encode('utf-8')
        myListSceneOrSwitch[(sw["idx"])] = {'Type':'switchlight','Name':myName}
    print('---------SwitchName----------')
    return myListSceneOrSwitch

def BuildActionSlotList(intent):
    intentSwitchList=list()
    intentSwitchActionList=list()
    intentSwitchState='None' #by default if no action
    for (slot_value, slot) in intent.slots.items():
        print("Slot_value: "+slot_value)
        if slot_value=="action" or slot_value=="switch":
            for slot_value2 in slot.all():
              print("Slot_Value2: "+slot_value2.value)
    print("---------------------------------")
    for (slot_value, slot) in intent.slots.items():
        print("Slot_value: "+slot_value)
        if slot_value=="action":
            #NLU parsing does not preserve order of slot, thus it is impossible to have different action ON and OFF in the same intent=> keep only the first:
            if slot[0].slot_value.value.value=="TurnOn":
                intentSwitchState='On'
            else :
                intentSwitchState='Off'
            print("SchalterStatus: "+intentSwitchState)
        elif slot_value=="switch":
            for slot_value2 in slot.all():
                intentSwitchList.append(slot_value2.value)
                print("Slotvalue: "+slot_value2.value)

    if not intentSwitchState=='None':
        for mySwitch in intentSwitchList:
            intentSwitchActionList.append({'Name':mySwitch,'State':intentSwitchState})
            print(mySwitch+"------>"+intentSwitchState)
    return intentSwitchActionList

def curlCmd(idx,myCmd,myParam,conf):
    command_url="http://"+conf.get("secret").get("hostname")+':'+conf.get("secret").get("port")+'/json.htm?type=command&param='+myParam+'&idx='+str(idx)+'&switchcmd='+myCmd
    ignore_result = requests.get(command_url)


def ActionneEntity(name,action,myListSceneOrSwitch,conf):
    #derived from nice work of https://github.com/iMartyn/domoticz-snips
    lowest_distance = MAX_JARO_DISTANCE
    lowest_idx = 65534
    lowest_name = "Unknown"
    MyWord=name
    DomoticzRealName=""
    print("ActionneEntity: "+MyWord)
    for idx,scene in myListSceneOrSwitch.items():
        print(str(scene['Name'],'utf-8'))
        distance = 1-jellyfish.jaro_distance(str(scene['Name'],'utf-8'), MyWord)
    #    print "Distance is "+str(distance)
        if distance < lowest_distance:
    #        print "Low enough and lowest!"
            lowest_distance = distance
            lowest_idx = idx
            lowest_name = scene['Name']
            lowest_Type= scene['Type']
    if lowest_distance < MAX_JARO_DISTANCE:
        #print (lowest_Type)
        DomoticzRealName=str(lowest_name,'utf-8')
        print("ActionneEntity: "+DomoticzRealName)
        #print(lowest_idx)
        curlCmd(lowest_idx,action,lowest_Type,conf)
        return True,DomoticzRealName
        hermes.publish_end_session(intent_message.session_id, "Einschalten "+lowest_name)
    else:
        return False,DomoticzRealName


def subscribe_intent_callback(hermes, intentMessage):    
    conf = read_configuration_file(CONFIG_INI)
    print(conf)
    #a=IntentClassifierResult(intentMessage).intent_name
    hermes.publish_continue_session(intentMessage.session_id, u"OK, aber?",["ryanrudak:switch","ryanrudak:dimmBefehle"])
    if len(intentMessage.slots.OrdreDivers) > 0:
     print('---------OrdreDivers----------')
     action_wrapperOrdreDirect(hermes, intentMessage, conf)
    else:
     print('---------Ordre Action----------')
     action_wrapperOrdre(hermes, intentMessage, conf)


def action_wrapperOrdreDirect(hermes, intentMessage, conf):
    myListSceneOrSwitch=dict()
    myListSceneOrSwitch= getSceneNames(conf,myListSceneOrSwitch)
    actionText = u"{}".format(str(intentMessage.slots.OrdreDivers.first().value))
    print("actionText "+actionText)
    DomoticzRealName=""
    MyAction=ActionneEntity(actionText,'On',myListSceneOrSwitch,conf)
    result_sentence = u"OK. Du hast {} angefordert.".format(str(MyAction[1]))  # The response that will be said out loud by the TTS engine.
    if MyAction[0] :
        hermes.publish_end_session(intentMessage.session_id, result_sentence)
    else:
        print("pas d action")
        hermes.publish_end_session(intentMessage.session_id, u"Entschuldigung, es ist etwas schief gegangen.")


def action_wrapperOrdre(hermes, intentMessage, conf):
    myListSceneOrSwitch=dict()
    myListSceneOrSwitch= getSceneNames(conf,myListSceneOrSwitch)
    print("Scenen ermitteln")
    myListSceneOrSwitch= getSwitchNames(conf,myListSceneOrSwitch)
    print("Schalter ermitteln")
    intentSwitchActionList=BuildActionSlotList(intentMessage)
    actionText=""
    myAction = True
    for intentSwitchAction in intentSwitchActionList:
        print("intentSwitchAction")
        Match= ActionneEntity(intentSwitchAction["Name"],intentSwitchAction["State"],myListSceneOrSwitch,conf)
        DomoticzRealName=Match[1]
        myAction=myAction and Match[0]
        if intentSwitchAction["State"]=="On":
            texte = u"Einschalten"
        else:
            texte = u"Ausschalten"
        actionText=u'{}, {} {}'.format(actionText,texte,str(DomoticzRealName))
    if myAction and len(intentSwitchActionList)>0:
        hermes.publish_end_session(intentMessage.session_id, actionText)
    else:
        hermes.publish_end_session(intentMessage.session_id, u"Entschuldigung, ich habe es nicht verstanden.")


if __name__ == "__main__":
    mqtt_opts = MqttOptions()
    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intent("ryanrudak:switch", subscribe_intent_callback) \
        .subscribe_intent("ryanrudak:dimmBefehle", subscribe_intent_callback) \
         .start()
