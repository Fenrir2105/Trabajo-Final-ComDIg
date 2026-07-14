# -*- coding: utf-8 -*-
"""
Universidad de Cuenca
Facultad de Ingeniería
Carrera de Ingeniería en Telecomunicaciones
Comunicaciones Digitales

Trabajo 2: Implementación Discreta de Modulación Multiportadora: OFDM
Simulador Núcleo de OFDM en Python (Soporte para 4 usuarios e imágenes)
"""

import numpy as np
import scipy.signal as signal
import matplotlib
# Configurar matplotlib para que no intente abrir ventanas GUI (modo no interactivo)
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

# =============================================================================
# MAPEO Y DESMAPEO DE CONSTELACIONES (BPSK, QPSK, 16-QAM, 64-QAM)
# =============================================================================

def qam_map(bits, modulation):
    """
    Mapea un arreglo de bits a símbolos complejos de la constelación elegida.
    """
    bits = np.array(bits).astype(int)
    if modulation == 'BPSK':
        symbols = 2 * bits - 1
        return symbols.astype(complex)
    
    elif modulation == 'QPSK':
        if len(bits) % 2 != 0:
            raise ValueError("Para QPSK, el número de bits debe ser múltiplo de 2.")
        bits = bits.reshape(-1, 2)
        I = 2 * bits[:, 0] - 1
        Q = 2 * bits[:, 1] - 1
        return (I + 1j * Q) / np.sqrt(2)
    
    elif modulation == '16-QAM':
        if len(bits) % 4 != 0:
            raise ValueError("Para 16-QAM, el número de bits debe ser múltiplo de 4.")
        bits = bits.reshape(-1, 4)
        gray_map = {(0, 0): -3, (0, 1): -1, (1, 1): 1, (1, 0): 3}
        I = np.array([gray_map[tuple(b)] for b in bits[:, 0:2]])
        Q = np.array([gray_map[tuple(b)] for b in bits[:, 2:4]])
        return (I + 1j * Q) / np.sqrt(10)
    
    elif modulation == '64-QAM':
        if len(bits) % 6 != 0:
            raise ValueError("Para 64-QAM, el número de bits debe ser múltiplo de 6.")
        bits = bits.reshape(-1, 6)
        gray_map = {
            (0, 0, 0): -7, (0, 0, 1): -5, (0, 1, 1): -3, (0, 1, 0): -1,
            (1, 1, 0): 1, (1, 1, 1): 3, (1, 0, 1): 5, (1, 0, 0): 7
        }
        I = np.array([gray_map[tuple(b)] for b in bits[:, 0:3]])
        Q = np.array([gray_map[tuple(b)] for b in bits[:, 3:6]])
        return (I + 1j * Q) / np.sqrt(42)
    
    else:
        raise ValueError(f"Modulación no soportada: {modulation}")

def qam_demap(symbols, modulation):
    """
    Desmapea símbolos complejos recibidos a un arreglo de bits usando decisión de máxima verosimilitud.
    """
    if modulation == 'BPSK':
        return (np.real(symbols) > 0).astype(int)
    
    elif modulation == 'QPSK':
        b0 = (np.real(symbols) > 0).astype(int)
        b1 = (np.imag(symbols) > 0).astype(int)
        return np.column_stack((b0, b1)).flatten()
    
    elif modulation == '16-QAM':
        gray_map_1d = {(0, 0): -3, (0, 1): -1, (1, 1): 1, (1, 0): 3}
        points = []
        bit_blocks = []
        for b_I, val_I in gray_map_1d.items():
            for b_Q, val_Q in gray_map_1d.items():
                points.append((val_I + 1j * val_Q) / np.sqrt(10))
                bit_blocks.append(np.array(b_I + b_Q))
        points = np.array(points)
        
        distances = np.abs(symbols[:, np.newaxis] - points[np.newaxis, :])
        closest_indices = np.argmin(distances, axis=1)
        return np.concatenate([bit_blocks[idx] for idx in closest_indices])
    
    elif modulation == '64-QAM':
        gray_map_1d = {
            (0, 0, 0): -7, (0, 0, 1): -5, (0, 1, 1): -3, (0, 1, 0): -1,
            (1, 1, 0): 1, (1, 1, 1): 3, (1, 0, 1): 5, (1, 0, 0): 7
        }
        points = []
        bit_blocks = []
        for b_I, val_I in gray_map_1d.items():
            for b_Q, val_Q in gray_map_1d.items():
                points.append((val_I + 1j * val_Q) / np.sqrt(42))
                bit_blocks.append(np.array(b_I + b_Q))
        points = np.array(points)
        
        distances = np.abs(symbols[:, np.newaxis] - points[np.newaxis, :])
        closest_indices = np.argmin(distances, axis=1)
        return np.concatenate([bit_blocks[idx] for idx in closest_indices])
    
    else:
        raise ValueError(f"Modulación no soportada: {modulation}")

# =============================================================================
# FILTRO BAJO PASO (LPF) SIN RETARDO DE FASE
# =============================================================================

def lowpass_filter(data, cutoff, fs, order=5):
    """
    Aplica un filtro Butterworth bajo paso de fase cero (filtfilt) para evitar retardos.
    """
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
    return signal.filtfilt(b, a, data)

# =============================================================================
# CADENA DE SIMULACIÓN OFDM MULTI-USUARIO (4 USUARIOS)
# =============================================================================

def simulate_ofdm_4user(mod_u1, mod_u2, mod_u3, mod_u4, snr_db, attenuation, 
                        bits_u1=None, bits_u2=None, bits_u3=None, bits_u4=None):
    """
    Simula la transmisión OFDM para 4 usuarios dividiendo las 64 subportadoras equitativamente (16 cada uno).
    """
    # Parámetros del sistema
    N = 64          # Subportadoras totales
    N_cp = 16       # Prefijo Cíclico
    L = 8           # Factor de sobremuestreo
    fs_bb = 20e6    # Frecuencia de muestreo base (20 MHz)
    fs_rf = fs_bb * L  # Frecuencia RF (160 MHz)
    f0 = 30e6       # Frecuencia portadora (30 MHz)
    
    # Asignación equitativa de subportadoras (16 por usuario)
    user1_carriers = np.arange(0, 16)
    user2_carriers = np.arange(16, 32)
    user3_carriers = np.arange(32, 48)
    user4_carriers = np.arange(48, 64)
    
    bits_per_sym = {'BPSK': 1, 'QPSK': 2, '16-QAM': 4, '64-QAM': 6}
    
    bps_u1 = bits_per_sym[mod_u1]
    bps_u2 = bits_per_sym[mod_u2]
    bits_u3_bps = bits_per_sym[mod_u3]
    bits_u4_bps = bits_per_sym[mod_u4]
    
    # Si no se proveen bits, generamos datos aleatorios por defecto (24576 bits c/u, equivale a 64x64/4 en bytes)
    default_length = 24576
    np.random.seed(42)
    if bits_u1 is None: bits_u1 = np.random.randint(0, 2, default_length)
    if bits_u2 is None: bits_u2 = np.random.randint(0, 2, default_length)
    if bits_u3 is None: bits_u3 = np.random.randint(0, 2, default_length)
    if bits_u4 is None: bits_u4 = np.random.randint(0, 2, default_length)
    
    # Guardar las longitudes originales de bits para des-padear
    len_u1 = len(bits_u1)
    len_u2 = len(bits_u2)
    len_u3 = len(bits_u3)
    len_u4 = len(bits_u4)
    
    # Calcular cuántos símbolos OFDM necesitamos según la cantidad de bits y la modulación de cada usuario
    M_u1 = int(np.ceil(len_u1 / (16 * bps_u1)))
    M_u2 = int(np.ceil(len_u2 / (16 * bps_u2)))
    M_u3 = int(np.ceil(len_u3 / (16 * bits_u3_bps)))
    M_u4 = int(np.ceil(len_u4 / (16 * bits_u4_bps)))
    
    # El número total de símbolos OFDM a transmitir será el máximo requerido por cualquier usuario
    num_symbols = max(M_u1, M_u2, M_u3, M_u4)
    
    # Padear bits con ceros para completar exactamente la capacidad del bloque OFDM
    req_u1 = 16 * num_symbols * bps_u1
    req_u2 = 16 * num_symbols * bps_u2
    req_u3 = 16 * num_symbols * bits_u3_bps
    req_u4 = 16 * num_symbols * bits_u4_bps
    
    bits_u1_padded = np.pad(bits_u1, (0, req_u1 - len_u1), 'constant')
    bits_u2_padded = np.pad(bits_u2, (0, req_u2 - len_u2), 'constant')
    bits_u3_padded = np.pad(bits_u3, (0, req_u3 - len_u3), 'constant')
    bits_u4_padded = np.pad(bits_u4, (0, req_u4 - len_u4), 'constant')
    
    # Mapear bits a símbolos QAM
    symbols_u1 = qam_map(bits_u1_padded, mod_u1)
    symbols_u2 = qam_map(bits_u2_padded, mod_u2)
    symbols_u3 = qam_map(bits_u3_padded, mod_u3)
    symbols_u4 = qam_map(bits_u4_padded, mod_u4)
    
    # Estructurar en matrices de (num_symbols x 16 subportadoras)
    sym_matrix_u1 = symbols_u1.reshape(num_symbols, 16)
    sym_matrix_u2 = symbols_u2.reshape(num_symbols, 16)
    sym_matrix_u3 = symbols_u3.reshape(num_symbols, 16)
    sym_matrix_u4 = symbols_u4.reshape(num_symbols, 16)
    
    # Matriz en el dominio de la frecuencia (num_symbols x 64)
    X = np.zeros((num_symbols, N), dtype=complex)
    X[:, user1_carriers] = sym_matrix_u1
    X[:, user2_carriers] = sym_matrix_u2
    X[:, user3_carriers] = sym_matrix_u3
    X[:, user4_carriers] = sym_matrix_u4
    
    # 1. Modulación IFFT
    x_time = np.fft.ifft(X, n=N, axis=1)
    
    # 2. Agregar Prefijo Cíclico
    x_cp = np.hstack((x_time[:, -N_cp:], x_time))
    
    # 3. Serialización
    s_bb = x_cp.flatten()
    
    # 4. Interpolación por factor L=8
    s_bb_up = signal.resample(s_bb, len(s_bb) * L)
    
    # 5. Upconversion a Portadora RF
    t = np.arange(len(s_bb_up)) / fs_rf
    s_rf = np.real(s_bb_up * np.exp(1j * 2 * np.pi * f0 * t))
    
    # =============================================================================
    # CANAL AWGN CON ATENUACIÓN
    # =============================================================================
    s_received = attenuation * s_rf
    P_rx = np.mean(s_received ** 2)
    snr_linear = 10 ** (snr_db / 10)
    P_noise = P_rx / snr_linear if snr_linear > 0 else 1e-5
    noise = np.random.normal(0, np.sqrt(P_noise), len(s_received))
    r_rf = s_received + noise
    
    # =============================================================================
    # RECEPTOR OFDM
    # =============================================================================
    # 1. Downconversion
    r_demod = 2 * r_rf * np.exp(-1j * 2 * np.pi * f0 * t)
    
    # 2. Filtro LPF (Fase Cero)
    r_filtered_real = lowpass_filter(np.real(r_demod), cutoff=12.5e6, fs=fs_rf)
    r_filtered_imag = lowpass_filter(np.imag(r_demod), cutoff=12.5e6, fs=fs_rf)
    r_filtered = r_filtered_real + 1j * r_filtered_imag
    
    # 3. Decimación
    r_bb = r_filtered[::L]
    r_bb = r_bb[:num_symbols * (N + N_cp)]
    
    # 4. Des-serialización y Remoción de CP
    r_bb_matrix = r_bb.reshape(num_symbols, N + N_cp)
    y_time = r_bb_matrix[:, N_cp:]
    
    # 5. Demodulación FFT
    Y = np.fft.fft(y_time, n=N, axis=1)
    
    # 6. Extracción de símbolos de subportadoras
    rec_u1 = Y[:, user1_carriers].flatten()
    rec_u2 = Y[:, user2_carriers].flatten()
    rec_u3 = Y[:, user3_carriers].flatten()
    rec_u4 = Y[:, user4_carriers].flatten()
    
    # Ecualización de amplitud por el factor de atenuación
    eq_u1 = rec_u1 / attenuation if attenuation > 0 else rec_u1
    eq_u2 = rec_u2 / attenuation if attenuation > 0 else rec_u2
    eq_u3 = rec_u3 / attenuation if attenuation > 0 else rec_u3
    eq_u4 = rec_u4 / attenuation if attenuation > 0 else rec_u4
    
    # 7. Desmapeo QAM a Bits
    dec_u1_padded = qam_demap(eq_u1, mod_u1)
    dec_u2_padded = qam_demap(eq_u2, mod_u2)
    dec_u3_padded = qam_demap(eq_u3, mod_u3)
    dec_u4_padded = qam_demap(eq_u4, mod_u4)
    
    # Cortar los bits al tamaño original de los datos
    dec_u1 = dec_u1_padded[:len_u1]
    dec_u2 = dec_u2_padded[:len_u2]
    dec_u3 = dec_u3_padded[:len_u3]
    dec_u4 = dec_u4_padded[:len_u4]
    
    # 8. Tasa de Error de Bits (BER)
    ber_u1 = np.mean(bits_u1 != dec_u1) if len_u1 > 0 else 0.0
    ber_u2 = np.mean(bits_u2 != dec_u2) if len_u2 > 0 else 0.0
    ber_u3 = np.mean(bits_u3 != dec_u3) if len_u3 > 0 else 0.0
    ber_u4 = np.mean(bits_u4 != dec_u4) if len_u4 > 0 else 0.0
    
    # =============================================================================
    # GENERACIÓN DE GRÁFICAS DE 4 USUARIOS
    # =============================================================================
    plots = {}
    
    # Configurar estilo visual oscuro de matplotlib
    plt.rcParams.update({
        'text.color': 'white',
        'axes.labelcolor': 'white',
        'xtick.color': 'white',
        'ytick.color': 'white',
        'grid.color': '#444444',
        'figure.facecolor': '#11121d',
        'axes.facecolor': '#161726'
    })
    
    # --- Gráfica 1: Constelaciones 2x2 ---
    fig, axs = plt.subplots(2, 2, figsize=(10, 8.5))
    
    users_data = [
        (eq_u1, mod_u1, bps_u1, '#00f2fe', 'Usuario 1', axs[0, 0]),
        (eq_u2, mod_u2, bps_u2, '#10ac84', 'Usuario 2', axs[0, 1]),
        (eq_u3, mod_u3, bits_u3_bps, '#a18cd1', 'Usuario 3', axs[1, 0]),
        (eq_u4, mod_u4, bits_u4_bps, '#ff9f43', 'Usuario 4', axs[1, 1])
    ]
    
    for eq_symbols, mod, bps, color, name, ax in users_data:
        ax.scatter(np.real(eq_symbols), np.imag(eq_symbols), color=color, alpha=0.4, label='Recibidos', s=10)
        # Teóricos
        all_bits = np.array([list(map(int, np.binary_repr(i, width=bps))) for i in range(2**bps)]).flatten()
        ref_symbols = qam_map(all_bits, mod)
        ax.scatter(np.real(ref_symbols), np.imag(ref_symbols), color='#ff007f', marker='x', s=50, linewidth=2, label='Teóricos', zorder=5)
        ax.set_title(f'{name} ({mod})')
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.axhline(0, color='white', linewidth=0.6, alpha=0.4)
        ax.axvline(0, color='white', linewidth=0.6, alpha=0.4)
        ax.legend(facecolor='#11121d', edgecolor='none', labelcolor='white', loc='upper right', fontsize=8)
    
    plt.tight_layout()
    plots['constellation'] = fig_to_base64(fig)
    plt.close(fig)
    
    # --- Gráfica 2: Espectro PSD ---
    fig, ax = plt.subplots(figsize=(10, 4.2))
    f_tx, Pxx_tx = signal.welch(s_rf, fs_rf, nperseg=1024)
    f_rx, Pxx_rx = signal.welch(r_rf, fs_rf, nperseg=1024)
    
    ax.plot((f_tx - f0)/1e6, 10 * np.log10(Pxx_tx + 1e-15), color='#00f2fe', label='TX OFDM (Combinado 4 Usuarios)', linewidth=1.5)
    ax.plot((f_rx - f0)/1e6, 10 * np.log10(Pxx_rx + 1e-15), color='#ff007f', label='RX OFDM + Ruido', linewidth=1, alpha=0.6)
    
    # Colorear las bandas de los usuarios en el espectro para una visualización increíble
    # En banda base, la señal de 20 MHz va de -10 MHz a 10 MHz.
    # Dado que N=64, cada usuario ocupa 16/64 = 25% del total de subportadoras (5 MHz c/u).
    # En frecuencia relativa (después de fftshift):
    # - User 3 (32-47) ocupa el centro a la derecha: 0 MHz a 5 MHz
    # - User 4 (48-63) ocupa la derecha: -10 MHz a -5 MHz
    # - User 1 (0-15) ocupa el centro a la izquierda: -5 MHz a 0 MHz
    # - User 2 (16-31) ocupa la izquierda: 5 MHz a 10 MHz
    # (Esto se debe al orden FFT y shift. Mostramos de forma simplificada)
    ax.axvspan(-10, -5, color='#ff9f43', alpha=0.08, label='Banda U4')
    ax.axvspan(-5, 0, color='#00f2fe', alpha=0.08, label='Banda U1')
    ax.axvspan(0, 5, color='#a18cd1', alpha=0.08, label='Banda U3')
    ax.axvspan(5, 10, color='#10ac84', alpha=0.08, label='Banda U2')
    
    ax.set_title('PSD en RF con 4 Usuarios (Canales Compartidos Equitativamente)')
    ax.set_xlabel('Frecuencia Relativa a la Portadora (MHz)')
    ax.set_ylabel('Potencia Espectral (dB/Hz)')
    ax.set_xlim(-14, 14)
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend(facecolor='#11121d', edgecolor='none', labelcolor='white', ncol=3)
    
    plt.tight_layout()
    plots['spectrum'] = fig_to_base64(fig)
    plt.close(fig)
    
    # --- Gráfica 3: Señal en el Tiempo ---
    fig, ax = plt.subplots(figsize=(10, 3.8))
    symbol_samples_rf = (N + N_cp) * L
    start_idx = 0
    end_idx = symbol_samples_rf
    
    t_plot = t[start_idx:end_idx] * 1e6
    sig_bb_plot = np.real(s_bb_up[start_idx:end_idx])
    sig_rf_plot = s_rf[start_idx:end_idx]
    cp_duration_us = (N_cp * L) / fs_rf * 1e6
    
    ax.plot(t_plot, sig_bb_plot, color='#a18cd1', label='Banda Base Combinada Re{x(t)}', linewidth=1.5)
    ax.plot(t_plot, sig_rf_plot, color='#fbc2eb', label='Señal RF s(t) de Transmisión', linewidth=1, alpha=0.7)
    ax.axvspan(0, cp_duration_us, color='#343a40', alpha=0.4, label='Prefijo Cíclico (CP)')
    
    ax.set_title('Señal Transmitida en el Tiempo (Detalle de 1er Símbolo OFDM Combinado)')
    ax.set_xlabel('Tiempo (µs)')
    ax.set_ylabel('Amplitud')
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend(facecolor='#11121d', edgecolor='none', labelcolor='white')
    
    plt.tight_layout()
    plots['time_domain'] = fig_to_base64(fig)
    plt.close(fig)
    
    return {
        'ber_user1': float(ber_u1),
        'ber_user2': float(ber_u2),
        'ber_user3': float(ber_u3),
        'ber_user4': float(ber_u4),
        'decoded_bits_u1': dec_u1.tolist(),
        'decoded_bits_u2': dec_u2.tolist(),
        'decoded_bits_u3': dec_u3.tolist(),
        'decoded_bits_u4': dec_u4.tolist(),
        'plots': plots
    }

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{image_base64}"
