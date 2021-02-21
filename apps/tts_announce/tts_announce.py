import pytz
import random
import appdaemon.plugins.hass.hassapi as hass
import time
import queue
import requests 
import math
import mutagen
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from io import BytesIO
from datetime import datetime, timedelta


class tts_announce(hass.Hass):

    def initialize(self):
        self.q_sound = queue.Queue()
        self.speaker_free_at = datetime.now()
        self.listen_event(self.tts_announce,  "tts_announce")
        if "ha_url" in self.args:
            self.ha_url = self.args["ha_url"]
        else:    
            self.log("Missing 'ha_url' parameter in apps.yaml")
        if "tts_language" in self.args:
            self.tts_language = self.args["tts_language"]
        else:    
            self.log("Missing 'tts_language' parameter in apps.yaml")
        if "tts_platform" in self.args:
            self.platform = self.args["tts_platform"]
        else:    
            self.log("Missing 'tts_platform' parameter in apps.yaml")
        self.speaker = None
        if "speaker" in self.args:
            self.speaker = self.args["speaker"]
        self.debug = False
        if "debug" in self.args:
            self.debug = self.args["debug"]
            if self.debug:
                self.log("Debug mode on")
        self.extra_delay_if_sleeps=False
        if "extra_delay_if_sleeps" in self.args:
            self.extra_delay_if_sleeps = self.args["extra_delay_if_sleeps"]
            if self.extra_delay_if_sleeps:
                self.log("Extra delay switched on")
        self.media_path = '/local/media/'
        if "media_path" in self.args:
            self.media_path = self.args["media_path"]
            self.log("Media path set as "+self.media_path)
        if "night_volume" in self.args:
            self.night_volume = self.args["night_volume"]
        else:
            self.night_volume = 0
        if "day_volume" in self.args:
            self.day_volume = self.args["day_volume"]
        else: 
            self.day_volume = 0

    def tts_announce(self, event, data, args):
        tts_file = None
        len_tts = 0
        len_snd = 0
        len_total = 0
        if data is not None:
            text = None
            if 'message' in data:
                text = data.get("message")
                options = {}
                language = self.tts_language
                gender =  "female"
                if "language" in data:
                    language = data.get("language")
                    voice = f"{language}-Wavenet-A"
                    speed = 1
                    if language == "en-GB":
                        speed = 0.9
                    options = {
                        "voice" : voice,
                        "gender" : gender,
                        "speed" : speed
                    }

                try:
                    self.log("TTS for text: '"+text+"'")
                    headers = {'Authorization' : 'Bearer ' + self.args["speech_token"]}
                    sdata = {'message': text, 'platform': self.platform, 'language': language, 'options': options }
                    response = requests.post(self.ha_url+'/api/tts_get_url', headers=headers, json=sdata)
                    if (response.status_code == 200):
                        tts_file = response.json()['url']
                        self.debug_log("TTS: "+tts_file)
                        r = requests.get(tts_file)
                        audio = MP3(BytesIO(r.content))
                        len_tts = audio.info.length
                        self.debug_log("TTS length is "+str(len_tts))
                    else:    
                        self.log("Problem with TTS")
                        return
                except:
                    self.log("TTS exception")
                    return

            speaker = self.speaker
            if "speaker" in data:
                speaker = data.get("speaker")
            if speaker is None:
                self.log("No speaker as parameter for event call nor in apps.yaml")
                return

            if self.get_state(speaker)=="unavailable":
                self.log("Speaker '"+speaker+"' is unavailable.")
                return

            filename = None
            if "filename" in data:
                filename = data.get("filename")

            if filename is None and text is None:
                self.log("No text nor filename parameter")
                return

            delay = None
            if "delay" in data:
                delay = data.get("delay")

            if filename is not None and filename>'':
                try:
                    r = requests.get(self.ha_url + self.media_path + filename)
                    ext = filename[-3:].upper()
                    if ext=="MP3":
                        audio = MP3(BytesIO(r.content))    
                    elif ext=="OGG":
                        audio = OggVorbis(BytesIO(r.content))
                    else:
                        audio = mutagen.File(BytesIO(r.content))
                    len_snd = audio.info.length
                except:
                    self.log("Exception when trying to get file length for '"+self.ha_url + self.media_path + filename+"'")
                    return

                self.debug_log("File length is "+str(len_snd)+" of '" + filename + "'")
                if delay is not None:
                    len_snd = delay
                    self.debug_log("But length set as "+str(delay)+" from parameter")

                len_snd = math.ceil(len_snd)
                if (len_snd % 1) > 0.8:
                    len_snd += 1
                    self.debug_log("So lenghtening delay with 1 sec")

                if self.extra_delay_if_sleeps and self.get_state(speaker)=="off": 
                    len_snd += 3
                    self.debug_log("Lenghtening delay with 3 secs")

            self.debug_log("Full length is "+str(len_snd + len_tts))
            can_play_now = False
            if (datetime.now()>self.speaker_free_at):
                can_play_now = True
                self.debug_log("Speaker '"+speaker+"' is free now")
            else:
                self.debug_log("Waiting for the speaker '"+speaker+"' to be free after "+str(self.speaker_free_at.time()))

            volume = 0
            if self.day_volume > 0:
                volume = self.day_volume
            if str(datetime.now().time()) > "22:00:00" or str(datetime.now().time()) < "05:00:00":
                volume = self.night_volume

            if volume > 0:
                try:
                    self.call_service("media_player/volume_set", entity_id=speaker, volume_level=volume)
                except:
                    self.log("Exception when trying to set volume on speaker '"+speaker+"'")
                    return
                self.debug_log("Volume of speaker '"+speaker+"' set to "+str(volume))

            if can_play_now:
                if filename is None:
                    self.sound(speaker=speaker, filename=tts_file, options=options)
                else:    
                    self.sound(speaker=speaker, filename=filename)
                    if tts_file is not None:
                        play_tts_at = (datetime.now() + timedelta(0, math.ceil(len_snd))).time()
                        self.debug_log("Delaying text to "+str(play_tts_at))
                        timer = self.run_once(self.delayed_sound, play_tts_at, speaker=speaker, filename=tts_file)
                        self.q_sound.put(timer)   
                self.speaker_free_at = datetime.now()
            else:    
                if filename is not None:
                    play_sound_at = self.speaker_free_at.time()
                    self.debug_log("Delaying file "+ filename + " to " + str(play_sound_at))
                    timer = self.run_once(self.delayed_sound, play_sound_at, speaker=speaker, filename=filename)
                    self.q_sound.put(timer)   

                if tts_file is not None:
                    play_tts_at = (self.speaker_free_at + timedelta(0, math.ceil(len_snd))).time()
                    self.debug_log("Delaying text to "+str(play_tts_at))
                    timer = self.run_once(self.delayed_sound, play_tts_at, speaker=speaker, filename=tts_file)
                    self.q_sound.put(timer)                   

            self.speaker_free_at += timedelta(0, math.ceil(len_snd) + math.ceil(len_tts) + 1)
            self.debug_log("Speaker will be free after "+str(self.speaker_free_at.time()))
        else:
            self.debug_log("No data")

    def debug_log(self, message):
        if self.debug:
            self.log(message)

    def delayed_sound(self, kwargs):
        if not self.q_sound.empty():
            self.cancel_timer(self.q_sound.get())
        if kwargs is not None and 'filename' in kwargs and 'speaker' in kwargs:
            self.sound(speaker=kwargs.get("speaker"), filename=kwargs.get("filename"))

    def sound(self, **kwargs):
        if kwargs is not None and 'filename' in kwargs and 'speaker' in kwargs:
            try:
                self.call_service("media_player/play_media", entity_id=kwargs.get("speaker"), media_content_id=kwargs.get("filename"), media_content_type="music")
                self.log("Playing file '" + kwargs.get("filename") + "'")
            except:
                self.log("Exception when trying to play file '"+ kwargs.get("filename") +"' on '"+speaker+"'")
