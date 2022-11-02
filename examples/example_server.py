#!/usr/bin/env python3

# Copyright 2017, 2022 National Research Foundation (SARAO)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import asyncio
import enum
import logging
import signal
import time
from typing import Tuple

import aiokatcp


class Foo(enum.Enum):
    ABC_DEF = 1
    GHI_K = 2


class Total(aiokatcp.AggregateSensor):
    def __init__(self, target):
        super().__init__(target=target, sensor_type=int, name="total")

    def update_aggregate(self, updated_sensor, reading, old_reading):
        if updated_sensor is None:
            # Instantiation, calculate total for sensors already in target.
            total = sum(
                sensor.value for sensor in self.target.values() if self.filter_aggregate(sensor)
            )
            return aiokatcp.Reading(time.time(), aiokatcp.Sensor.Status.NOMINAL, total)
        new_value = self.value
        if old_reading is not None:  # Will be None if this is a new sensor being added
            new_value -= old_reading.value  # Remove the previous value from the sum
        if reading is not None:  # Will be None if this is a sensor being removed
            new_value += reading.value  # Add the new value to the sum
        return aiokatcp.Reading(
            updated_sensor.timestamp,
            aiokatcp.Sensor.Status.NOMINAL,
            new_value,
        )

    def filter_aggregate(self, sensor):
        """Return true for int sensors which aren't self."""
        return sensor.stype is int and sensor is not self


class Server(aiokatcp.DeviceServer):
    VERSION = "testapi-1.0"
    BUILD_STATE = "testapi-1.0.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sensor = aiokatcp.Sensor(
            int,
            "counter-queries",
            "number of ?counter queries",
            default=0,
            initial_status=aiokatcp.Sensor.Status.NOMINAL,
        )
        self.sensors.add(sensor)
        sensor = aiokatcp.Sensor(Foo, "foo", "nonsense")
        self.sensors.add(sensor)
        self.add_service_task(asyncio.create_task(self._service_task()))

        total_sensor = Total(self.sensors)
        self.sensors.add(total_sensor)
        self.add_service_task(asyncio.create_task(self._alter_sensors()))

    async def request_echo(self, ctx, *args: str) -> Tuple:
        """Return the arguments to the caller"""
        return tuple(args)

    async def request_sleep(self, ctx, time: float) -> None:
        """Sleep for some amount of time"""
        await asyncio.sleep(time)

    async def request_fail(self, ctx, arg: str) -> None:
        """Request that always returns a failure reply"""
        raise aiokatcp.FailReply(arg + " is no good")

    async def request_crash(self, ctx) -> None:
        """Request that always raises an exception"""
        raise RuntimeError("help I've fallen over and can't get up")

    async def request_counter(self, ctx) -> None:
        """Increment counter-queries"""
        self.sensors["counter-queries"].value += 1

    async def _service_task(self) -> None:
        """Example service task that broadcasts to clients."""
        while True:
            await asyncio.sleep(10)
            self.mass_inform("hello", "Hi I am a service task")

    async def _alter_sensors(self) -> None:
        """Example service task that adds and removes a fixed sensor.

        This demonstrate's the aggregate sensor's ability to add and remove
        values from its total.
        """
        await asyncio.sleep(10)
        self.mass_inform("add", "I'm going to add a fixed sensor")
        sensor = aiokatcp.Sensor(int, "fixed-value", default=7)
        self.sensors.add(sensor)

        await asyncio.sleep(10)
        self.mass_inform("remove", "I'm going to remove the fixed sensor")
        self.sensors.remove(sensor)


async def main():
    server = Server("localhost", 4444)
    handler = Server.LogHandler(server)
    logging.getLogger().addHandler(handler)
    await server.start()
    asyncio.get_event_loop().add_signal_handler(signal.SIGINT, server.halt)
    await server.join()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    loop.run_until_complete(main())
    loop.close()
