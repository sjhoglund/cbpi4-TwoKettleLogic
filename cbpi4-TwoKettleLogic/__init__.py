
# -*- coding: utf-8 -*-
import os
from aiohttp import web
import logging
from unittest.mock import MagicMock, patch
import asyncio
import random
from cbpi.api import *
from cbpi.api.step import CBPiStep, StepResult
from cbpi.api.dataclasses import NotificationAction, NotificationType

logger = logging.getLogger(__name__)

@parameters([
     Property.Number(label="Temp_Kettle_1", configurable=True),
     Property.Sensor(label="Sensor_Kettle_1"),
     Property.Kettle(label="Kettle_1"),
     Property.Number(label="Temp_Kettle_2", configurable=True),
     Property.Sensor(label="Sensor_Kettle_2"),
     Property.Kettle(label="Kettle_2")
])

class TwoKettleStep(CBPiStep):
    
    async def NextStep(self, **kwargs):
        await self.next()

    async def on_start(self):
        
        self.kettle=self.get_kettle(self.props.get("Kettle_1", None))
        self.kettle.target_temp = int(self.props.get("Temp_Kettle_1", 0))
        self.kettle=self.get_kettle(self.props.get("Kettle_2", None))
        self.kettle.target_temp = int(self.props.get("Temp_Kettle_2", 0))  
        
        await self.push_update()

    async def run(self):
        while self.running == True:
            await asyncio.sleep(1)
            sensor_value_1 = self.get_sensor_value(self.props.get("Sensor_Kettle_1", None)).get("value")
            sensor_value_2 = self.get_sensor_value(self.props.get("Sensor_Kettle_2", None)).get("value")
            set_temp_1 = int(self.props.get("Temp_Kettle_1",0))
            set_temp_2 = int(self.props.get("Temp_Kettle_2",0))
            if sensor_value_1 >= set_temp_1 and sensor_value_2 >= set_temp_2:
                self.cbpi.notify(self.name, "Kettle Temps Reached!", NotificationType.INFO)
        return StepResult.DONE

def setup(cbpi):
    cbpi.plugin.register("TwoKettleLogic", TwoKettleStep)
    pass