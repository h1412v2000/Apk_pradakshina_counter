import os
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window

# Import services
from services.db_service import DatabaseService
from services.sensor_service import SensorService
from services.geofence_service import GeofenceService

# Import screens
from screens.home_screen import HomeScreen
from screens.set_target_screen import SetTargetScreen
from screens.live_tracking_screen import LiveTrackingScreen
from screens.temple_profile_screen import TempleProfileScreen
from screens.sankalpa_screen import SankalpaScreen
from screens.lifetime_stats_screen import LifetimeStatsScreen
from screens.festival_calendar_screen import FestivalCalendarScreen

# Set windows size for testing on PC
Window.size = (360, 640)

class PradakshinaApp(App):
    def build(self):
        self.title = "Pradakshina Tracker"
        
        # Initialize services
        self.db = DatabaseService()
        self.sensor = SensorService()
        self.geofence = GeofenceService()
        
        # Enable GPS
        self.sensor.start_gps()
        
        # Screen manager
        sm = ScreenManager()
        
        # Register screens
        sm.add_widget(HomeScreen(db_service=self.db, sensor_service=self.sensor, geofence_service=self.geofence, name='home'))
        sm.add_widget(SetTargetScreen(name='set_target'))
        sm.add_widget(LiveTrackingScreen(db_service=self.db, sensor_service=self.sensor, geofence_service=self.geofence, name='live_tracking'))
        sm.add_widget(TempleProfileScreen(db_service=self.db, sensor_service=self.sensor, geofence_service=self.geofence, name='temples'))
        sm.add_widget(SankalpaScreen(db_service=self.db, name='sankalpa'))
        sm.add_widget(LifetimeStatsScreen(db_service=self.db, name='stats'))
        sm.add_widget(FestivalCalendarScreen(name='calendar'))
        
        return sm

    def on_stop(self):
        self.sensor.stop_gps()

if __name__ == '__main__':
    PradakshinaApp().run()
