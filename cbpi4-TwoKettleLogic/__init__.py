
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
             Property.Kettle(label="Kettle_2")])

class TwoKettleStep(CBPiStep):
    
    async def NextStep(self, **kwargs):
        await self.next()

    async def on_timer_done(self,timer):
        self.summary = "MashIn Temp reached."
        await self.push_update()
        self.cbpi.notify(self.name, 'MashIn Temp reached. Time to dough-in! Move to next step', action=[NotificationAction("Next Step", self.NextStep)])

    async def on_timer_update(self,timer, seconds):
        await self.push_update()

    async def on_start(self):
        self.port = str(self.cbpi.static_config.get('port',8000))
        self.setKettleTarget(self.props.get("Kettle_1", None), self.get_kettle(self.props.get("Kettle_1", None)), int(self.props.get("Temp_1", 0)))
        self.setKettleTarget(self.props.get("Kettle_2", None), self.get_kettle(self.props.get("Kettle_2", None)), int(self.props.get("Temp_2", 0)))
        self.summary = "Waiting for Target Temp..."
        if self.timer is None:
            self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        await self.push_update()

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        self.setKettleTarget(self.props.get("Kettle_1", None), self.get_kettle(self.props.get("Kettle_1", None)), 0)
        self.setKettleTarget(self.props.get("Kettle_2", None), self.get_kettle(self.props.get("Kettle_2", None)), 0)
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

    async def setKettleTarget(self, kettle_name, kettle_info, kettle_temp):
        self.kettle = kettle_info
        self.kettle.target_temp = kettle_temp
        await self.push_update()
        self.cbpi.notify(self.name, 'Kettle: '+kettle_name+'| Temp set: '+kettle_temp, NotificationType.INFO)


def setup(cbpi):
    cbpi.plugin.register("TwoKettleLogic", TwoKettleStep)
    pass