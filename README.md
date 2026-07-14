# Trabajo 2: Implementación Discreta de Modulación Multiportadora (OFDM)

Autor: Diego Fernando Portilla Loja  
Institución: Universidad de Cuenca - Carrera de Ingeniería en Telecomunicaciones  
Asignatura: Comunicaciones Digitales  

## Descripción del Proyecto

Este proyecto implementa un simulador a nivel discreto de un sistema de transmisión basado en modulación multiportadora OFDM (Orthogonal Frequency-Division Multiplexing). El sistema simula la transmisión y recepción simultánea de datos para 4 usuarios compartiendo un canal AWGN (Ruido Blanco Gaussiano Aditivo) con atenuación. 

El simulador cuenta con una interfaz web desarrollada en Flask que permite transmitir señales de audio (sintetizadas o cargadas por el usuario), procesarlas a través de toda la cadena OFDM y escuchar el resultado decodificado, visualizando en tiempo real el efecto del ruido y la atenuación en las diferentes modulaciones soportadas.

## Características Principales

* Soporte Multi-usuario: Multiplexación de 4 usuarios simultáneos, asignando 16 subportadoras a cada uno (64 subportadoras en total).
* Modulaciones Flexibles: Selección independiente de esquemas de modulación (BPSK, QPSK, 16-QAM, 64-QAM) para cada usuario.
* Transmisión de Audio: Capacidad de enviar un arpegio de audio sintetizado por defecto o procesar archivos de audio cargados en formato WAV.
* Simulación de Canal: Inclusión de atenuación y ruido AWGN configurable mediante la relación Señal a Ruido (SNR) en dB.
* Visualización Gráfica: Generación automática de diagramas de constelación (teóricos vs recibidos), espectro de densidad de potencia (PSD) en RF y dominio del tiempo.
* Métricas de Rendimiento: Cálculo de la Tasa de Error de Bits (BER) individual para cada usuario.

---

## Estructura de Archivos

* app.py: Servidor web principal en Flask. Maneja las rutas HTTP, la conversión de audio a bits (y viceversa), el empaquetado en base64 y la comunicación con el núcleo de simulación.
* ofdm_simulation.py: Núcleo matemático de la simulación OFDM. Contiene el mapeo/desmapeo QAM, las operaciones IFFT/FFT, la inserción del prefijo cíclico, el canal AWGN y el filtrado.
* requirements.txt: Lista de dependencias de Python necesarias para ejecutar el proyecto.
* test_ofdm.py / test_app_logic.py: Scripts de pruebas para validar la lógica matemática y de audio sin necesidad de levantar el servidor web.

Carpetas del Sistema Web:
* templates/
  * index.html: Archivo de estructura HTML que define la interfaz gráfica de usuario servida por Flask.
* static/
  * style.css: Hoja de estilos que proporciona el diseño visual moderno (modo oscuro) a la interfaz.
  * script.js: Lógica del lado del cliente (Frontend) encargada de la interactividad, recolección de parámetros, envío de peticiones asíncronas al servidor y actualización de gráficas y audios.
* __pycache__/
  * app.cpython-311.pyc / ofdm_simulation.cpython-311.pyc: Archivos binarios compilados automáticamente por Python para mejorar los tiempos de carga de ejecución.

---

## Requisitos Previos

Asegúrate de tener Python 3 instalado en tu sistema. Se recomienda el uso de un entorno virtual para no crear conflictos con las dependencias globales.

## Instalación

1. Clona o descarga este repositorio en tu máquina local asegurándote de mantener la estructura de carpetas (static/ y templates/).
2. Abre una terminal y navega hasta el directorio raíz del proyecto.
3. Instala las dependencias necesarias ejecutando el siguiente comando:

pip install -r requirements.txt

---

## Ejecución del Servidor Web

Para iniciar la aplicación y acceder a la interfaz gráfica, ejecuta el archivo principal de Flask:

python app.py

Una vez que la consola indique que el servidor está corriendo, abre tu navegador web de preferencia y dirígete a:

http://127.0.0.1:5000

## Uso de la Interfaz Web

1. Configuración de Modulaciones: En la pantalla principal, selecciona el esquema de modulación (BPSK, QPSK, 16-QAM o 64-QAM) que utilizará cada uno de los 4 usuarios.
2. Parámetros del Canal: Ajusta el nivel de SNR (en dB) para definir la cantidad de ruido en el canal y modifica el factor de atenuación según lo requieras.
3. Audio: Por defecto, el sistema generará un arpegio musical. Si deseas probar con tu propio audio, asegúrate de que sea un archivo en formato WAV corto (se recomienda un máximo de 3 segundos para tiempos de simulación óptimos).
4. Simular: Haz clic en el botón de simulación. El procesamiento tomará unos segundos dependiendo de los parámetros y la longitud del audio.
5. Análisis de Resultados: Una vez finalizado, podrás escuchar el audio original frente al audio recibido por cada usuario, observar el nivel de error (BER) y analizar las gráficas de constelación y espectro generadas.
