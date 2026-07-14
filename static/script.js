document.addEventListener('DOMContentLoaded', () => {
    // Inputs
    const selectModU1 = document.getElementById('mod_user1');
    const selectModU2 = document.getElementById('mod_user2');
    const selectModU3 = document.getElementById('mod_user3');
    const selectModU4 = document.getElementById('mod_user4');
    
    const sliderSNR = document.getElementById('snr_db');
    const labelSNR = document.getElementById('snr_val');
    
    const sliderAtt = document.getElementById('attenuation');
    const labelAtt = document.getElementById('att_val');
    
    const inputAudio = document.getElementById('audio_input');
    const btnRunSim = document.getElementById('run_sim');
    
    // Outputs - Metrics
    const valBER1 = document.getElementById('ber_u1_val');
    const valBER2 = document.getElementById('ber_u2_val');
    const valBER3 = document.getElementById('ber_u3_val');
    const valBER4 = document.getElementById('ber_u4_val');
    
    const badgeU1 = document.getElementById('mod_u1_badge');
    const badgeU2 = document.getElementById('mod_u2_badge');
    const badgeU3 = document.getElementById('mod_u3_badge');
    const badgeU4 = document.getElementById('mod_u4_badge');
    const badgeSNR = document.getElementById('snr_badge');
    
    // Outputs - Audio Elements
    const audioOriginal = document.getElementById('audio_original');
    const audioReceivedU1 = document.getElementById('audio_received_u1');
    const audioReceivedU2 = document.getElementById('audio_received_u2');
    const audioReceivedU3 = document.getElementById('audio_received_u3');
    const audioReceivedU4 = document.getElementById('audio_received_u4');
    
    // Outputs - Plot Images
    const imgConst = document.getElementById('img_constellation');
    const imgSpec = document.getElementById('img_spectrum');
    const imgTime = document.getElementById('img_time_domain');
    
    // Outputs - Explanations
    const expU1 = document.getElementById('exp_u1');
    const expU2 = document.getElementById('exp_u2');
    const expU3 = document.getElementById('exp_u3');
    const expU4 = document.getElementById('exp_u4');
    
    const loader = document.getElementById('loader');

    // Global variable to store uploaded audio in base64
    let uploadedAudioBase64 = "";

    // Update slider labels dynamically
    sliderSNR.addEventListener('input', (e) => {
        labelSNR.textContent = `${e.target.value} dB`;
        badgeSNR.textContent = `SNR: ${e.target.value} dB`;
    });

    sliderAtt.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value).toFixed(2);
        labelAtt.textContent = val;
    });

    // Update explanation labels when user changes modulations
    selectModU1.addEventListener('change', (e) => { expU1.textContent = e.target.value; });
    selectModU2.addEventListener('change', (e) => { expU2.textContent = e.target.value; });
    selectModU3.addEventListener('change', (e) => { expU3.textContent = e.target.value; });
    selectModU4.addEventListener('change', (e) => { expU4.textContent = e.target.value; });

    // Handle audio file upload
    inputAudio.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            uploadedAudioBase64 = event.target.result;
            // Trigger simulation automatically when audio is loaded
            runSimulation();
        };
        reader.readAsDataURL(file);
    });

    // Run simulation
    async function runSimulation() {
        loader.classList.remove('hidden');

        // Sync explanation labels initially
        expU1.textContent = selectModU1.value;
        expU2.textContent = selectModU2.value;
        expU3.textContent = selectModU3.value;
        expU4.textContent = selectModU4.value;

        const params = {
            mod_user1: selectModU1.value,
            mod_user2: selectModU2.value,
            mod_user3: selectModU3.value,
            mod_user4: selectModU4.value,
            snr_db: parseFloat(sliderSNR.value),
            attenuation: parseFloat(sliderAtt.value),
            audio_base64: uploadedAudioBase64
        };

        try {
            const response = await fetch('/simulate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(params)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ocurrió un error en el servidor.');
            }

            const data = await response.json();

            // 1. Update Bit Error Rates (BER)
            valBER1.textContent = data.ber_user1.toFixed(5);
            valBER2.textContent = data.ber_user2.toFixed(5);
            valBER3.textContent = data.ber_user3.toFixed(5);
            valBER4.textContent = data.ber_user4.toFixed(5);

            updateBERColor(valBER1, data.ber_user1);
            updateBERColor(valBER2, data.ber_user2);
            updateBERColor(valBER3, data.ber_user3);
            updateBERColor(valBER4, data.ber_user4);

            // 2. Update Badges
            badgeU1.textContent = selectModU1.value;
            badgeU2.textContent = selectModU2.value;
            badgeU3.textContent = selectModU3.value;
            badgeU4.textContent = selectModU4.value;

            // 3. Update Audio Players
            audioOriginal.src = data.original_audio;
            audioReceivedU1.src = data.received_audio_u1;
            audioReceivedU2.src = data.received_audio_u2;
            audioReceivedU3.src = data.received_audio_u3;
            audioReceivedU4.src = data.received_audio_u4;

            // Force browser to reload audio sources
            audioOriginal.load();
            audioReceivedU1.load();
            audioReceivedU2.load();
            audioReceivedU3.load();
            audioReceivedU4.load();

            // 4. Update Plot Images
            imgConst.src = data.plots.constellation;
            imgSpec.src = data.plots.spectrum;
            imgTime.src = data.plots.time_domain;

        } catch (error) {
            console.error('Error executing simulation:', error);
            alert(`Error de simulación: ${error.message}`);
        } finally {
            loader.classList.add('hidden');
        }
    }

    function updateBERColor(element, berVal) {
        if (berVal === 0) {
            element.style.color = '#10ac84'; // Emerald Green
        } else if (berVal > 0.05) {
            element.style.color = '#ff007f'; // Hot Pink
        } else {
            element.style.color = '#ff9f43'; // Orange
        }
    }

    // Attach click listener to run button
    btnRunSim.addEventListener('click', runSimulation);

    // Initial simulation run with the default arpeggio audio
    runSimulation();
});
