import sys
sys.path.append('.')
import numpy as np
from ofdm_simulation import simulate_ofdm_4user
from app import create_default_audio

# 1. Synthesize default audio arpeggio
fs, audio_samples = create_default_audio()
print("Audio Synthesized. Sample Rate:", fs, "Length:", len(audio_samples), "Dtype:", audio_samples.dtype)

# 2. Convert audio to bits
orig_dtype = audio_samples.dtype
bytes_per_sample = audio_samples.itemsize

# Pad to make bytes multiple of 4
total_bytes = len(audio_samples) * bytes_per_sample
remainder = total_bytes % 4
if remainder != 0:
    pad_bytes = 4 - remainder
    pad_samples = int(np.ceil(pad_bytes / bytes_per_sample))
    audio_samples = np.pad(audio_samples, (0, pad_samples), 'constant')

raw_bytes = audio_samples.tobytes()
uint8_array = np.frombuffer(raw_bytes, dtype=np.uint8)
bits = np.unpackbits(uint8_array)

# Cast to signed int for ofdm simulation math
bits = bits.astype(int)

# Copy the ENTIRE bitstream to all 4 users
bits_u1 = bits
bits_u2 = bits
bits_u3 = bits
bits_u4 = bits

# 3. Simulate OFDM
results = simulate_ofdm_4user(
    mod_u1='BPSK',
    mod_u2='QPSK',
    mod_u3='16-QAM',
    mod_u4='64-QAM',
    snr_db=40.0,
    attenuation=1.0,
    bits_u1=bits_u1,
    bits_u2=bits_u2,
    bits_u3=bits_u3,
    bits_u4=bits_u4
)

# 4. Decodificar por separado para cada usuario
dec_u1 = np.array(results['decoded_bits_u1'], dtype=np.uint8)
dec_u2 = np.array(results['decoded_bits_u2'], dtype=np.uint8)
dec_u3 = np.array(results['decoded_bits_u3'], dtype=np.uint8)
dec_u4 = np.array(results['decoded_bits_u4'], dtype=np.uint8)

# 5. Convert bits back to audio samples for each user
rec_samples_u1 = np.frombuffer(np.packbits(dec_u1).tobytes(), dtype=orig_dtype)
rec_samples_u2 = np.frombuffer(np.packbits(dec_u2).tobytes(), dtype=orig_dtype)
rec_samples_u3 = np.frombuffer(np.packbits(dec_u3).tobytes(), dtype=orig_dtype)
rec_samples_u4 = np.frombuffer(np.packbits(dec_u4).tobytes(), dtype=orig_dtype)

# 6. Verify correct decoding (0.0 BER and identical arrays)
print("BER User 1:", results['ber_user1'])
print("BER User 2:", results['ber_user2'])
print("BER User 3:", results['ber_user3'])
print("BER User 4:", results['ber_user4'])

print("U1 samples identical:", np.array_equal(audio_samples, rec_samples_u1))
print("U2 samples identical:", np.array_equal(audio_samples, rec_samples_u2))
print("U3 samples identical:", np.array_equal(audio_samples, rec_samples_u3))
print("U4 samples identical:", np.array_equal(audio_samples, rec_samples_u4))
