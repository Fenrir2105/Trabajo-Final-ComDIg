import sys
sys.path.append('.')
import numpy as np
from ofdm_simulation import simulate_ofdm_4user

# Generate random bits explicitly
np.random.seed(42)
b1 = np.random.randint(0, 2, 24576)
b2 = np.random.randint(0, 2, 24576)
b3 = np.random.randint(0, 2, 24576)
b4 = np.random.randint(0, 2, 24576)

results = simulate_ofdm_4user(
    mod_u1='BPSK',
    mod_u2='QPSK',
    mod_u3='16-QAM',
    mod_u4='64-QAM',
    snr_db=34.0,
    attenuation=0.85,
    bits_u1=b1,
    bits_u2=b2,
    bits_u3=b3,
    bits_u4=b4
)

print("BER User 1:", results['ber_user1'])
print("BER User 2:", results['ber_user2'])
print("BER User 3:", results['ber_user3'])
print("BER User 4:", results['ber_user4'])
