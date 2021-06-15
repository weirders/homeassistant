import datetime

import hassapi as hass


#
# App to turn lights on when motion detected then off again after a delay
# Doubleclick on the switch, within specified timeframe, will disable motion activated mode
#
# NOTES:
# 1. its LIST of sensors and LIST of entities. Stick to the supplied apps.yaml example structure.
# 2. this app switches on the sensor going OFF, meaning, start app, then trigger motion for it to start. Take into account the time your sensor needs to turn to an off state.
#
# Args:
#
# sensors: list of binary sensor to use as trigger, all sensors must be meet condition
# entities : list of entities to turn on when detecting motion, can be a light, script, scene or anything else that can be turned on
# off_delay: amount of time in minutes after turning on to turn off again. If not specified defaults to 1 minute.
# doubleclick_delay: amount of time in miliseconds that counts as doubleclick
#
# example apps.yaml
#
# living_room_lights:
#   module: MotionLightsPlus
#   class: MotionLightsPlus
#   sensors:
#     - binary_sensor.lumi_lumi_sensor_motion_6a002301_ias_zone
#   entities:
#     - light.shelly_shdm_1_d3e2a5
#   off_delay: 5
#   doubleclick_delay: 1000
#
# Release Notes
#
# Version 1.0:
#   Initial Version

class MotionLightsPlus(hass.Hass):
    def initialize(self):

        self.handle = None

        # Check some Params
        if 'doubleclick_delay' in self.args:
            self.dcdelay = self.args["doubleclick_delay"] * 1000
        else:
            self.dcdelay = 2000000
        self.trigger = False
        self.state = {}
        self.auto = False
        # Subscribe to sensors and create dic to hold state
        if "sensors" in self.args:
            for sensor in self.args["sensors"]:
                self.listen_state(self.motion, sensor)
                self.state[sensor] = 0
        else:
            self.log("No sensors specified")
        self.switches = {}

        if "entities" in self.args:
            for ent in self.args["entities"]:
                self.listen_state(self.switch, ent)
                state = self.get_state(ent)
                self.switches[ent] = self.get_now()
                if state == 'on':
                    self.auto = True
        else:
            self.log("No entities specified, nothing to switch")
        if self.auto == True:
            self.log('Started with motion activation ON as one of the lights was on.')
        else:
            self.log('Started with motion activation OFF as none of the lights were on.')

    def switch(self, entity, attribute, old, new, kwargs):
        if self.trigger == False:
           
            if old == "on" and new == "off":
                self.log('turning off motion activation')
                self.auto = False
                self.switches[entity] = self.get_now()

            if old == "off" and new == "on":
                if self.get_now() - self.switches[entity] < datetime.timedelta(microseconds=self.dcdelay):
                    self.log(f"Turning on {self.args['entities']} on without motion activation")
                else:
                    self.log(f"Turning on {self.args['entities']} on with motion activation")
                    self.auto = True

        self.trigger = False

    def motion(self, entity, attribute, old, new, kwargs):
        if self.auto == False: return
        
        if new == "on":
            self.cancel()
            for ent in self.args["entities"]:
                if self.get_state(ent) == 'on': return
            if "entities" in self.args:
                self.log(f"Motion detected: turning {self.args['entities']} on")
                self.light_on()
       
        if new == "off":
            if "off_delay" in self.args:
                delay = self.args["off_delay"]
            else:
                delay = 1
            self.cancel()
            self.handle = self.run_in(self.light_off, delay * 60)

    def light_on(self):
        if "entities" in self.args:
            for ent in self.args["entities"]:
                self.trigger = True
                self.turn_on(ent)

    def light_off(self, kwargs):
        if "entities" in self.args:
            self.log(f"Turning {self.args['entities']} off")
            for ent in self.args["entities"]:
                self.trigger = True
                self.turn_off(ent)

    def cancel(self):
        if self.handle:
            self.cancel_timer(self.handle)
            self.handle = None
