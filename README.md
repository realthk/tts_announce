# TTS Announce


Automations often can be triggered unexpectedly. If an automation creates sound announcement (either just by playing a sound effect, or by  text-to-speech), it can be a problem if another automation is also triggered while the first one is still playing its sound, because the second sound will stop the first.

I couldn't find any media player capable of dynamic queues, that is the reason for this Appdaemon script.

Appdaemon cannot create service callable from Home Assistant, but it can listen to events, which has the same result.


Have this in appdeamon's config:

```
python_packages:
  - mutagen
```


## Example appdaemon/apps/apps.yaml
```
tts_announce:
  class: tts_announce
  module: tts_announce
  speech_token: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  ha_url: http://192.168.x.xxx:8123
  tts_platform: google_cloud
  tts_language: hu-HU
  speaker: media_player.mpd
  night_volume: 0.6
  day_volume: 0.8
  debug: True
  extra_delay_if_sleeps: False
```  

Where 

---
Key | Required | Description | Default 
------------ | ------------- | ------------- | ------------- 
**speech_token** | True | a long lived token created in Home Assistant | None 
**ha_url**|True |is how you access Home Assistant on the local network.  It is used to access the TTS API, and also as url for the files to be played | None 
**tts_platform**|True|The same platform you specify in Home Assistant configuration.yaml under tts| None
**tts_language**|True|Default language for TTS. Can specify a different for any event call|None
**speaker**|True|Id of the media_player entity to play sounds on|None
**night_volume**|No|Volume level between 0 and 1 for the night (22-05) When set to 0 or left out from apps.yaml, no volume change will take place|0
**day_volume**|No|Volume level between 0 and 1 for the day (05-22) When set to 0 or left out from apps.yaml, no volume change will take place|0
**debug**|No|Log every detail of processing in Appdaemon's log when set to **True**|False
**extra_delay_if_sleeps**|No|Can be set to True for Google devices to have an extra 3 secs delay when the speaker is in "off" state, because it takes about 2 secs to wake it up|False
**media_path**|No|Sound effect files local path|/local/media/


**speech_token** can also be placed in ```secrets.yaml``` with ```apps.yaml``` containing
```
  speech_token: !secret speech_token
```  
just don't forget to restart Appdaemon after it, as it caches ```secrets.yaml```


## Using it from automations

TTS message started with a bell:

```
  action:
    - event: tts_announce
      event_data:
        filename: bells/proxima.ogg
        message: "Someone is at the door"
```

Where it could be used with either only "message:" specified, when no effect is required, or only with "filename:" parameter when no TTS is wanted.


Optionally the delay can also be specified for example when it is a long mp3
and only the first 5 seconds requied:
```
  action:
    - event: tts_announce
      event_data:
        filename: effects/very_long.mp3
        delay: 5
        message: "And this is the announcement"
```

Language speech parameter can also be specified instead of the default one.
```
  action:
    - event: tts_announce
      event_data:
        message: "Guten morgen schönheit!"
        language: de-DE
```

Randomized effect and message with template
  action:
```  
  - event: tts_announce
    event_data_template:
        filename: >
            {% if (range(1,100) | random | int) > 50 %}
            pumukli/jol_aludtal_kakaot.mp3
            {% else %}
            pumukli/jo_reggelt_kivanok.mp3
            {% endif %}        
        message: >-
            {{ [
            "First funny message",
            "Second",
            "Third"
            ] |random }}
```
