from pydub import AudioSegment
from pydub.playback import play

# Load original sound
sound = AudioSegment.from_mp3("sounds/defeat.mp3")

# Create higher pitch version (increase by 3 semitones)
higher_pitch = sound._spawn(sound.raw_data, overrides={
    "frame_rate": int(sound.frame_rate * 1.189207115)
})
higher_pitch.export("sounds/defeat_high.mp3", format="mp3")

# Create lower pitch version (decrease by 3 semitones)
lower_pitch = sound._spawn(sound.raw_data, overrides={
    "frame_rate": int(sound.frame_rate * 0.840896415)
})
lower_pitch.export("sounds/defeat_low.mp3", format="mp3")

print("Created sounds/defeat_high.mp3 and sounds/defeat_low.mp3")