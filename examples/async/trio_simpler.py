'''Example shows the recommended way of how to run Kivy with a trio
event loop as just another async coroutine.
'''
import asks
import os
import trio

os.environ['KIVY_EVENTLOOP'] = 'trio'
asks.init('trio')

from kivy.app import App
from kivy.lang.builder import Builder
from kivy.uix.button import Button

    
kv = '''
BoxLayout:
    orientation: 'vertical'
    MyButton:
        id: btn
        text: 'Press me'
    Label:
        id: label
'''

class MyButton(Button):
    async def on_release(self):
        """ Download file reporting progress """
        self.disabled = True
        url = 'https://apod.nasa.gov/apod/image/1705/Arp273Main_HubblePestana_3079.jpg'
        downloaded = 0
        response = await asks.get(url, stream=True)
        async for chunk in response.body:
            downloaded += len(chunk)
            App.root.ids.label.text = "got %s of %s" % (downloaded, response.headers['content-length'])
        self.disabled = False
            

class MyApp(App):
    async def async_run(self):
        App.root = self.root = Builder.load_string(kv)
        await super().async_run()


if __name__ == '__main__':
    trio.run(MyApp().async_run)
 
