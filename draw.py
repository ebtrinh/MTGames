from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line
from kivy.config import Config
from kivy.clock import Clock
import ctypes
from ctypes import wintypes

# 1. FORCE MULTI-TOUCH CONFIGURATION
# This tells Kivy to listen to the Windows native touch input provider (WM_TOUCH)
# instead of just the mouse driver.
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.set('graphics', 'fullscreen', '0') # Set to 'auto' for full screen
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '600')


def disable_windows_touch_gestures():
    """Attempt to disable Windows touch gestures for the active window"""
    try:
        user32 = ctypes.windll.user32

        # Get the foreground window handle
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False

        # Define gesture config structure
        class GESTURECONFIG(ctypes.Structure):
            _fields_ = [
                ("dwID", wintypes.DWORD),
                ("dwWant", wintypes.DWORD),
                ("dwBlock", wintypes.DWORD),
            ]

        # Gesture IDs
        GC_ALLGESTURES = 0x00000001
        GC_PAN = 0x00000004
        GC_ZOOM = 0x00000003
        GC_ROTATE = 0x00000002
        GC_TWOFINGERTAP = 0x00000006
        GC_PRESSANDTAP = 0x00000007

        # Block all gestures
        gc = GESTURECONFIG()
        gc.dwID = 0  # All gestures
        gc.dwWant = 0
        gc.dwBlock = GC_ALLGESTURES

        # Try to set gesture config
        result = user32.SetGestureConfig(
            hwnd,
            0,  # Reserved
            1,  # Number of gesture configs
            ctypes.byref(gc),
            ctypes.sizeof(GESTURECONFIG)
        )

        print(f"[TouchGestures] SetGestureConfig result: {result}")
        return result != 0

    except Exception as e:
        print(f"[TouchGestures] Failed to disable gestures: {e}")
        return False

class TouchDraw(Widget):
    def on_touch_down(self, touch):
        # This function fires for EVERY new finger that touches the screen.
        # 'touch.ud' is a user-dictionary unique to that specific finger (ID).

        with self.canvas:
            # Assign a random color for each finger to prove multi-touch works
            Color(1, 1, 0) # Yellow lines

            # Start a line at the touch location
            # We store the line object in the touch's dictionary so we can add to it later
            touch.ud['line'] = Line(points=(touch.x, touch.y), width=2)

    def on_touch_move(self, touch):
        # This fires when a specific finger ID moves
        # We grab the specific line associated with THIS finger and add the new point
        if 'line' in touch.ud:
            touch.ud['line'].points += [touch.x, touch.y]

class MultiTouchApp(App):
    def build(self):
        return TouchDraw()

if __name__ == '__main__':
    MultiTouchApp().run()
