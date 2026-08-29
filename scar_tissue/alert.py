import sys

def play_tone(frequency=440, duration=0.5):
    try:
        if sys.platform == 'win32':
            import winsound
            winsound.Beep(frequency, int(duration * 1000))
        else:
            print('\\a', end='', flush=True)
    except: pass

def play_faaaaa():
    play_tone(280, 1.2)

def play_compound_alert(count):
    if count >= 2:
        play_faaaaa()
    else:
        play_tone(440, 0.3)
