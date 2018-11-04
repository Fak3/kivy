'''Async version of :mod:`kivy.app`.
===========================================
'''

import trio
from kivy.base import async_runTouchApp


class AsyncApp(object):

    async def async_run(self):
        '''Identical to :meth:`run`, but is a coroutine and can be
        scheduled in a running async event loop.

        .. versionadded:: 1.10.1
        '''
        self._run_prepare()
        async with trio.open_nursery() as nursery:
            self.nursery = nursery
            await async_runTouchApp()
        self.stop()
