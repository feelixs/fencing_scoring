from pydub import AudioSegment
from pydub.playback import play
from pydub.effects import normalize

# Load original sound
sound = AudioSegment.from_mp3("sounds/fencing_beep_edgy.mp3")

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

def create_edgy_sound(input_file, output_file, gain_db=2, headroom_db=1.0):
    """
    Create a version of the sound with more 'edge' by:
    1. Normalizing the audio
    2. Applying gain to increase volume
    3. Adding compression-like effect with headroom
    
    Args:
        input_file: Path to input MP3 file
        output_file: Path to save the processed MP3 file
        gain_db: Amount of gain to add in dB
        headroom_db: Headroom for normalization in dB
    """
    sound = AudioSegment.from_mp3(input_file)
    
    # Normalize the audio
    normalized = normalize(sound, headroom=headroom_db)
    
    # Add gain to increase volume and create more "edge"
    with_edge = normalized + gain_db
    
    # Export the processed sound
    with_edge.export(output_file, format="mp3")
    
    print(f"Created {output_file} with added edge effect")

# Create edgy version of fencing_beep.mp3
create_edgy_sound("sounds/fencing_beep.mp3", "sounds/fencing_beep_edgy.mp3")

print("Created sounds/defeat_high.mp3 and sounds/defeat_low.mp3")