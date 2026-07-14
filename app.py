# -*- coding: utf-8 -*-
"""
Universidad de Cuenca
Facultad de Ingeniería
Carrera de Ingeniería en Telecomunicaciones
Comunicaciones Digitales

Trabajo 2: Implementación Discreta de Modulación Multiportadora: OFDM
Servidor Web Flask (Transmisión de Audio y Música)
"""

from flask import Flask, render_template, request, jsonify
from ofdm_simulation import simulate_ofdm_4user
from scipy.io import wavfile
import numpy as np
import io
import base64

app = Flask(__name__)

def create_default_audio():
    """
    Sintetiza programáticamente un arpegio de 4 notas (Do, Mi, Sol, Do) en formato de 16-bit WAV mono a 8 kHz.
    Cada nota dura 0.75 segundos, coincidiendo con la franja de cada usuario.
    """
    fs = 8000
    duration = 3.0
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    data = np.zeros_like(t)
    
    # Notas: Do4 (261.63 Hz), Mi4 (329.63 Hz), Sol4 (392.00 Hz), Do5 (523.25 Hz)
    freqs = [261.63, 329.63, 392.00, 523.25]
    segment_len = len(t) // 4
    
    # Envoltura de desvanecimiento (fade) de 50 ms para evitar clics
    fade_len = int(fs * 0.05)
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)
    
    for i, f in enumerate(freqs):
        start = i * segment_len
        end = (i + 1) * segment_len
        t_seg = t[start:end]
        
        # Mezcla de fundamental + armónicos para un sonido más rico
        tone = (
            0.6 * np.sin(2 * np.pi * f * t_seg) +
            0.3 * np.sin(2 * np.pi * 2 * f * t_seg) +
            0.1 * np.sin(2 * np.pi * 3 * f * t_seg)
        )
        
        # Aplicar desvanecimiento
        tone[:fade_len] *= fade_in
        tone[-fade_len:] *= fade_out
        data[start:end] = tone
        
    # Escalar a enteros de 16 bits firmados
    audio_16 = (data * 32767).astype(np.int16)
    return fs, audio_16

def encode_audio_base64(fs, data):
    """
    Guarda los datos de audio en un buffer en memoria como archivo WAV y lo codifica en base64.
    """
    buf = io.BytesIO()
    wavfile.write(buf, fs, data)
    buf.seek(0)
    audio_b64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:audio/wav;base64,{audio_b64}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        mod_u1 = data.get('mod_user1', 'BPSK')
        mod_u2 = data.get('mod_user2', 'QPSK')
        mod_u3 = data.get('mod_user3', '16-QAM')
        mod_u4 = data.get('mod_user4', '64-QAM')
        
        snr_db = float(data.get('snr_db', 20.0))
        attenuation = float(data.get('attenuation', 1.0))
        audio_base64 = data.get('audio_base64', '')
        
        # 1. Cargar o sintetizar el audio
        if audio_base64:
            # Quitar cabecera base64
            if ',' in audio_base64:
                audio_base64 = audio_base64.split(',')[1]
            wav_data = base64.b64decode(audio_base64)
            fs, audio_samples = wavfile.read(io.BytesIO(wav_data))
            
            # Convertir a mono si es estéreo
            if len(audio_samples.shape) > 1:
                audio_samples = audio_samples[:, 0]
                
            # Limitar a un máximo de 3 segundos para evitar lentitud
            max_samples = 3 * fs
            if len(audio_samples) > max_samples:
                audio_samples = audio_samples[:max_samples]
        else:
            fs, audio_samples = create_default_audio()
            
        # Determinar el tipo de dato original del audio
        orig_dtype = audio_samples.dtype
        bytes_per_sample = audio_samples.itemsize
        
        # Rellenar con ceros (pad) para asegurar que el tamaño en bytes sea múltiplo de 4
        # (Esto garantiza que la cantidad de bits sea múltiplo de 32, divisible de forma exacta para 4 usuarios)
        total_bytes = len(audio_samples) * bytes_per_sample
        remainder = total_bytes % 4
        if remainder != 0:
            pad_bytes = 4 - remainder
            pad_samples = int(np.ceil(pad_bytes / bytes_per_sample))
            audio_samples = np.pad(audio_samples, (0, pad_samples), 'constant')
            
        # Convertir muestras de audio en bits
        raw_bytes = audio_samples.tobytes()
        uint8_array = np.frombuffer(raw_bytes, dtype=np.uint8)
        bits = np.unpackbits(uint8_array)
        
        # Convertir a int para evitar el bug de desbordamiento en operaciones matemáticas del simulador
        bits = bits.astype(int)
        
        # Cada usuario transmite la totalidad del audio completo simultáneamente
        bits_u1 = bits
        bits_u2 = bits
        bits_u3 = bits
        bits_u4 = bits
        
        # 2. Ejecutar simulación OFDM
        results = simulate_ofdm_4user(
            mod_u1=mod_u1,
            mod_u2=mod_u2,
            mod_u3=mod_u3,
            mod_u4=mod_u4,
            snr_db=snr_db,
            attenuation=attenuation,
            bits_u1=bits_u1,
            bits_u2=bits_u2,
            bits_u3=bits_u3,
            bits_u4=bits_u4
        )
        
        # 3. Decodificar los audios recibidos independientemente
        dec_u1 = np.array(results['decoded_bits_u1'], dtype=np.uint8)
        dec_u2 = np.array(results['decoded_bits_u2'], dtype=np.uint8)
        dec_u3 = np.array(results['decoded_bits_u3'], dtype=np.uint8)
        dec_u4 = np.array(results['decoded_bits_u4'], dtype=np.uint8)
        
        # Convertir bits a bytes e interpretar como muestras de audio para cada usuario
        rec_samples_u1 = np.frombuffer(np.packbits(dec_u1).tobytes(), dtype=orig_dtype)
        rec_samples_u2 = np.frombuffer(np.packbits(dec_u2).tobytes(), dtype=orig_dtype)
        rec_samples_u3 = np.frombuffer(np.packbits(dec_u3).tobytes(), dtype=orig_dtype)
        rec_samples_u4 = np.frombuffer(np.packbits(dec_u4).tobytes(), dtype=orig_dtype)
        
        # Generar base64 para los audios original y recibidos de los 4 usuarios
        original_audio_b64 = encode_audio_base64(fs, audio_samples)
        audio_b64_u1 = encode_audio_base64(fs, rec_samples_u1)
        audio_b64_u2 = encode_audio_base64(fs, rec_samples_u2)
        audio_b64_u3 = encode_audio_base64(fs, rec_samples_u3)
        audio_b64_u4 = encode_audio_base64(fs, rec_samples_u4)
        
        # Limpiar bits del JSON para optimizar
        results.pop('decoded_bits_u1')
        results.pop('decoded_bits_u2')
        results.pop('decoded_bits_u3')
        results.pop('decoded_bits_u4')
        
        # Adjuntar URIs de audio
        results['original_audio'] = original_audio_b64
        results['received_audio_u1'] = audio_b64_u1
        results['received_audio_u2'] = audio_b64_u2
        results['received_audio_u3'] = audio_b64_u3
        results['received_audio_u4'] = audio_b64_u4
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
