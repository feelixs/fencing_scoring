import os
import tempfile
import numpy as np
import soundfile as sf
import noisereduce as nr
from pydub import AudioSegment
from pydub.playback import play
from pydub.effects import normalize

# --- Noise Reduction Function ---

def remove_noise(input_file, output_file, prop_decrease=1.0, temp_wav_suffix="_temp_nr.wav"):
    """
    Removes noise from an MP3 file using noisereduce.

    Args:
        input_file (str): Path to the input MP3 file.
        output_file (str): Path to save the processed MP3 file.
        prop_decrease (float): How much the noise should be reduced (0.0 to 1.0).
                                1.0 attempts full reduction.
        temp_wav_suffix (str): Suffix for temporary WAV files.
    """
    print(f"Attempting noise reduction on {input_file}...")
    try:
        # Load MP3 using pydub
        audio = AudioSegment.from_mp3(input_file)

        # Create temporary WAV file path
        base_name = os.path.splitext(input_file)[0]
        temp_wav_path = base_name + temp_wav_suffix

        # Export to temporary WAV
        audio.export(temp_wav_path, format="wav")

        # Load WAV using soundfile for noisereduce
        rate, data = sf.read(temp_wav_path)

        # Ensure data is float for noisereduce
        if data.dtype != np.float32 and data.dtype != np.float64:
            # Convert integer PCM to float [-1.0, 1.0]
            if np.issubdtype(data.dtype, np.integer):
                max_val = np.iinfo(data.dtype).max
                data = data.astype(np.float32) / max_val
            else:
                # Attempt conversion if some other type, might fail
                data = data.astype(np.float32)


        # Perform noise reduction
        # Use the first second for noise profiling if stereo, else first half second
        noise_clip_duration = min(1.0, len(data) / rate / 2) # Use up to 1s or half the audio
        noise_clip_samples = int(noise_clip_duration * rate)

        if len(data.shape) > 1 and data.shape[1] > 1: # Stereo
             noise_clip = data[:noise_clip_samples, :]
        else: # Mono
             noise_clip = data[:noise_clip_samples]

        # Check if noise_clip is valid
        if noise_clip.size == 0:
             print(f"Warning: Could not get a noise clip from {input_file}. Skipping noise reduction.")
             reduced_noise_data = data # Skip reduction
        else:
             reduced_noise_data = nr.reduce_noise(y=data, sr=rate, y_noise=noise_clip, prop_decrease=prop_decrease)


        # Save reduced noise data back to the temporary WAV
        sf.write(temp_wav_path, reduced_noise_data, rate)

        # Load the processed WAV back with pydub
        processed_audio = AudioSegment.from_wav(temp_wav_path)

        # Export the final MP3
        processed_audio.export(output_file, format="mp3")
        print(f"Saved noise-reduced file to {output_file}")

    except Exception as e:
        print(f"Error during noise reduction for {input_file}: {e}")
    finally:
        # Clean up temporary WAV file
        if 'temp_wav_path' in locals() and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except OSError as e:
                print(f"Error removing temporary file {temp_wav_path}: {e}")


# --- Sound Creation Steps ---

# Define file paths
original_beep = "sounds/fencing_beep.mp3"
cleaned_beep = "sounds/fencing_beep_cleaned.mp3"
edgy_beep = "sounds/fencing_beep_edgy.mp3"
defeat_high = "sounds/defeat_high.mp3"
defeat_low = "sounds/defeat_low.mp3"

# 1. Remove noise from the original beep
remove_noise(original_beep, cleaned_beep)

# 2. Create edgy version from the *cleaned* beep
# (Function definition remains the same, but we call it with cleaned input)
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

create_edgy_sound(cleaned_beep, edgy_beep)


# 3. Create pitch-shifted versions from the *edgy* (and cleaned) beep
# Load the newly created edgy sound
sound = AudioSegment.from_mp3(edgy_beep)

# Create higher pitch version (increase by 3 semitones)
higher_pitch = sound._spawn(sound.raw_data, overrides={
    "frame_rate": int(sound.frame_rate * 1.189207115) # Approx +3 semitones
})
# Normalize the pitch-shifted sound to avoid clipping/volume issues
higher_pitch = normalize(higher_pitch)
higher_pitch.export(defeat_high, format="mp3")
print(f"Created {defeat_high}")

# Create lower pitch version (decrease by 3 semitones)
lower_pitch = sound._spawn(sound.raw_data, overrides={
    "frame_rate": int(sound.frame_rate * 0.840896415) # Approx -3 semitones
})
# Normalize the pitch-shifted sound
lower_pitch = normalize(lower_pitch)
lower_pitch.export(defeat_low, format="mp3")
print(f"Created {defeat_low}")


print("\nSound generation process complete.")
