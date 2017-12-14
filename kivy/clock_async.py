'''Async version of :mod:`kivy.clock`.
===========================================
'''

from kivy.compat import async_coroutine
import asyncio
import os

if os.environ.get('KIVY_EVENTLOOP', 'default') == 'trio':
    import trio
    _async_lib = trio

    @async_coroutine
    def wait_for(coro, t):
        with trio.move_on_after(t):
            yield from coro
else:
    _async_lib = asyncio
    wait_for = asyncio.wait_for


class AsyncClockBaseBehavior(object):

    @async_coroutine
    def async_idle(self):
        '''(internal) async version of :meth:`idle`.
        '''
        fps = self._max_fps
        if fps > 0:
            min_sleep = self.get_resolution()
            undershoot = 4 / 5. * min_sleep
            ready = self._check_ready

            slept = False
            done, sleeptime = ready(fps, min_sleep, undershoot)
            while not done:
                slept = True
                yield from _async_lib.sleep(sleeptime)
                done, sleeptime = ready(fps, min_sleep, undershoot)

            if not slept:
                yield from _async_lib.sleep(0)
        else:
            yield from _async_lib.sleep(0)

        current = self.time()
        self._dt = current - self._last_tick
        self._last_tick = current
        return current

    @async_coroutine
    def async_tick(self):
        '''async version of :meth:`tick`. '''
        self.pre_idle()
        ts = self.time()
        current = yield from self.async_idle()
        self.post_idle(ts, current)


class AsyncClockBaseInterruptBehavior(object):

    @async_coroutine
    def async_usleep(self, microseconds):
        self._async_event.clear()
        yield from wait_for(self._async_event.wait(), microseconds / 1000000.)

    @async_coroutine
    def async_idle(self):
        fps = self._max_fps
        event = self._async_event
        resolution = self.get_resolution()
        if fps > 0:
            done, sleeptime = self._check_ready(
                fps, resolution, 4 / 5. * resolution, event)
            if not done:
                yield from wait_for(event.wait(), sleeptime)
            else:
                yield from _async_lib.sleep(0)
        else:
            yield from _async_lib.sleep(0)

        current = self.time()
        self._dt = current - self._last_tick
        self._last_tick = current
        event.clear()
        # anything scheduled from now on, if scheduled for the upcoming frame
        # will cause a timeout of the event on the next idle due to on_schedule
        # `self._last_tick = current` must happen before clear, otherwise the
        # on_schedule computation is wrong when exec between the clear and
        # the `self._last_tick = current` bytecode.
        return current


class AsyncClockBaseFreeInterruptOnly(object):

    @async_coroutine
    def async_idle(self):
        fps = self._max_fps
        current = self.time()
        event = self._async_event
        if fps > 0:
            min_sleep = self.get_resolution()
            usleep = self.usleep
            undershoot = 4 / 5. * min_sleep
            min_t = self.get_min_free_timeout
            interupt_next_only = self.interupt_next_only

            sleeptime = 1 / fps - (current - self._last_tick)
            slept = False
            while sleeptime - undershoot > min_sleep:
                if event.is_set():
                    do_free = True
                else:
                    t = min_t()
                    if not t:
                        do_free = True
                    elif interupt_next_only:
                        do_free = False
                    else:
                        sleeptime = min(sleeptime, t - current)
                        do_free = sleeptime - undershoot <= min_sleep

                if do_free:
                    event.clear()
                    self._process_free_events(current)
                else:
                    slept = True
                    yield from wait_for(event.wait(), sleeptime - undershoot)
                current = self.time()
                sleeptime = 1 / fps - (current - self._last_tick)

            if not slept:
                yield from _async_lib.sleep(0)
        else:
            yield from _async_lib.sleep(0)

        self._dt = current - self._last_tick
        self._last_tick = current
        event.clear()  # this needs to stay after _last_tick
        return current
