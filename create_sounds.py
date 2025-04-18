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

        # Load WAV using soundfile, requesting float32 directly
        try:
            data, rate = sf.read(temp_wav_path, dtype='float32')
        except Exception as e:
            print(f"Error reading temporary WAV file {temp_wav_path} with soundfile: {e}")
            return False  # Indicate failure

        # Check if data read was successful and is a numpy array
        if not isinstance(data, np.ndarray) or data.size == 0:
            print(f"Failed to load valid audio data from {temp_wav_path}")
            return False  # Indicate failure

        # Perform noise reduction
        # Use up to the first second for noise profiling
        noise_clip_duration = min(1.0, len(data) / rate / 2)  # Use up to 1s or half the audio
        noise_clip_samples = int(noise_clip_duration * rate)

        if len(data.shape) > 1 and data.shape[1] > 1:  # Stereo
            noise_clip = data[:noise_clip_samples, :]
        else:  # Mono
            noise_clip = data[:noise_clip_samples]

        # Check if noise_clip is valid
        if noise_clip.size == 0:
            print(f"Warning: Could not get a valid noise clip (size 0) from {input_file}. Skipping noise reduction.")
            reduced_noise_data = data  # Skip reduction
        elif np.std(noise_clip) < 1e-10:  # Check if noise clip is essentially silent
            print(
                f"Warning: Noise clip from {input_file} is nearly silent (std dev < 1e-10). Skipping noise reduction to avoid potential errors.")
            reduced_noise_data = data  # Skip reduction
        else:
            # Perform noise reduction, catching potential runtime warnings
            with np.errstate(divide='ignore', invalid='ignore'):  # Suppress the specific warning if it still occurs
                reduced_noise_data = nr.reduce_noise(y=data, sr=rate, y_noise=noise_clip, prop_decrease=prop_decrease)


            # Save reduced noise data back to the temporary WAV
        sf.write(temp_wav_path, reduced_noise_data, rate)

        # Load the processed WAV back with pydub
        processed_audio = AudioSegment.from_wav(temp_wav_path)

        # Export the final MP3
        processed_audio.export(output_file, format="mp3")
        print(f"Saved noise-reduced file to {output_file}")
        return True  # Indicate success

    except Exception as e:
        print(f"Error during noise reduction processing for {input_file}: {e}")
        return False  # Indicate failure
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
print("--- Step 1: Noise Reduction ---")
noise_reduction_successful = remove_noise(original_beep, cleaned_beep)


# Define the function for creating edgy sound here so it's available regardless
# of whether noise reduction succeeded, but only call it if needed.
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
    return True  # Indicate success


# 2. Create edgy version
print("\n--- Step 2: Create Edgy Sound ---")
edgy_sound_created = False
source_for_edgy = None

if noise_reduction_successful:
    print(f"Using cleaned beep '{cleaned_beep}' as source.")
    source_for_edgy = cleaned_beep
    edgy_sound_created = create_edgy_sound(source_for_edgy, edgy_beep)
else:
    print(f"Warning: Noise reduction failed. Attempting to create edgy sound from original '{original_beep}'.")
    source_for_edgy = original_beep
    # Check if original exists before trying to use it
    if os.path.exists(source_for_edgy):
        edgy_sound_created = create_edgy_sound(source_for_edgy, edgy_beep)
    else:
        print(f"Error: Original beep '{original_beep}' not found. Cannot create edgy sound.")

# 3. Create pitch-shifted versions
print("\n--- Step 3: Create Pitch-Shifted Defeat Sounds ---")
if edgy_sound_created and os.path.exists(edgy_beep):
    print(f"Using edgy beep '{edgy_beep}' as source for pitch shifting.")
    # Load the edgy sound
    sound = AudioSegment.from_mp3(edgy_beep)

    # Create higher pitch version (increase by 3 semitones)
    higher_pitch = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * 1.189207115)  # Approx +3 semitones
    })
    # Normalize the pitch-shifted sound to avoid clipping/volume issues
    higher_pitch = normalize(higher_pitch)
    higher_pitch.export(defeat_high, format="mp3")
    print(f"Created {defeat_high}")

    # Create lower pitch version (decrease by 3 semitones)
    lower_pitch = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * 0.840896415)  # Approx -3 semitones
    })
    # Normalize the pitch-shifted sound
    lower_pitch = normalize(lower_pitch)
    lower_pitch.export(defeat_low, format="mp3")
    print(f"Created {defeat_low}")
else:
    print("Skipping pitch shifting because the edgy sound was not created successfully.")

print("\nSound generation process complete.")
