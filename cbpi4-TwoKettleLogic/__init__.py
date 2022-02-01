
import asyncio
import aiohttp
from aiohttp import web
from cbpi.api.step import CBPiStep, StepResult
from cbpi.api.timer import Timer
from cbpi.api.dataclasses import Kettle, Props
from datetime import datetime
import time
from cbpi.api import *
import logging
from socket import timeout
from typing import KeysView
from cbpi.api.config import ConfigType
from cbpi.api.base import CBPiBase
from voluptuous.schema_builder import message
from cbpi.api.dataclasses import NotificationAction, NotificationType
import numpy as np
import requests
import warnings

@parameters([Property.Number(label="Temp_1", configurable=True),
             Property.Sensor(label="Sensor_1"),
             Property.Kettle(label="Kettle_1"),
             Property.Number(label="Temp_2", configurable=True),
             Property.Sensor(label="Sensor_2"),
             Property.Kettle(label="Kettle_2"),
             Property.Select(label="AutoMode",options=["Yes","No"], description="Switch Kettlelogic automatically on and off -> Yes")])

class TwoKettleStep(CBPiStep):
    
    async def NextStep(self, **kwargs):
        await self.next()

    async def on_timer_done(self,timer):
        self.summary = "MashIn Temp reached."
        await self.push_update()
        self.cbpi.notify(self.name, 'MashIn Temp reached. Time to dough-in! Move to next step. Make sure auto is turned off!', action=[NotificationAction("Next Step", self.NextStep)])

    async def on_timer_update(self,timer, seconds):
        await self.push_update()

    async def on_start(self):
        self.port = str(self.cbpi.static_config.get('port',8000))
        self.AutoMode = True if self.props.get("AutoMode","No") == "Yes" else False
        self.kettle1=self.get_kettle(self.props.get("Kettle_1", None))
        self.kettle1.target_temp = int(self.props.get("Temp_1", 0))
        self.kettle2=self.get_kettle(self.props.get("Kettle_2", None))
        self.kettle2.target_temp = int(self.props.get("Temp_2", 0))
        if self.AutoMode == True:
            await self.setAutoMode(True)
        self.summary = "Waiting for Target Temp..."
        if self.timer is None:
            self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        await self.push_update()

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        if self.AutoMode == True:
            await self.setAutoMode(False)
        await self.push_update()

    async def run(self):
        while self.running == True:
           await asyncio.sleep(1)
           sensor_value_1 = self.get_sensor_value(self.props.get("Sensor_1", None)).get("value")
           sensor_value_2 = self.get_sensor_value(self.props.get("Sensor_2", None)).get("value")
           if sensor_value_1 >= int(self.props.get("Temp_1",0)) and sensor_value_2 >= int(self.props.get("Temp_2",0)) and self.timer.is_running is not True:
               self.timer.start()
               self.timer.is_running = True
        await self.push_update()
        return StepResult.DONE

    async def reset(self):
        self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
    
    async def setAutoMode(self, auto_state):
        try:
            if (self.kettle1.instance is None or self.kettle1.instance.state == False) and (self.kettle2.instance is None or self.kettle2.instance.state == False) and (auto_state is True):
                url1="http://127.0.0.1:" + self.port + "/kettle/"+ self.kettle1.id+"/toggle"
                url2="http://127.0.0.1:" + self.port + "/kettle/"+ self.kettle2.id+"/toggle"
                async with aiohttp.ClientSession() as session:
                    async with session.post(url1) as response1, session.post(url2) as response2:
                        return await response1.text()
                        await self.push_update()
            elif (self.kettle1.instance.state == True) and (self.kettle2.instance.state == True) and (auto_state is False):

                await self.kettle1.instance.stop()
                await self.kettle2.instance.stop()
                await self.push_update()

        except Exception as e:
            logging.error("Failed to switch on KettleLogic {} {}".format(self.kettle1.id, e))


def setup(cbpi):
    cbpi.plugin.register("TwoKettleLogic", TwoKettleStep)
    pass