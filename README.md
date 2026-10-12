# 🔬 SOVIC: Sistema Optomecatrónico con Visión Artificial para Clasificación de Lesiones Cervicales (LSIL / HSIL)

[![Status](https://img.shields.io/badge/Status-Protected%20Research-blue)]()
[![Hardware](https://img.shields.io/badge/Hardware-Raspberry%20Pi%205%20%7C%20ESP32C3-orange)]()
[![Tech Stack](https://img.shields.io/badge/Stack-Python%20%7C%20Tkinter%20%7C%20OpenCV%20%7C%20TensorFlow-green)]()

---

## 🇺🇸 ENGLISH VERSION

### 💡 The Problem & Motivation
In regions with high cervical cancer incidence and limited healthcare resources, medical staff face a massive bottleneck: **analyzing thousands of manual Pap smear slides**, where up to 98% of samples are negative (NILM). Reviewing these manually causes severe visual fatigue, diagnostic backlogs, and delayed treatments—a critical delay that can lead to preventable cancer fatalities.

### 🚀 What is SOVIC?
**SOVIC** (*Sistema Optomecatrónico con Visión Artificial para Clasificación de Lesiones Cervicales*) is an automated, low-cost Point-of-Care (PoC) computer-aided triage system designed to automate the traditional Pap smear workflow without modifying existing laboratory equipment. 

Instead of forcing a specialist to manually inspect thousands of slides, SOVIC replicates human dexterity and visual analysis through an integrated mechatronic approach:
- **The Eyes:** A non-invasive universal microscope camera captures real-time high-resolution optical fields.
- **The Fingers & Hands:** Custom 3D-printed mechanical adapters, toothed belts, and NEMA 17 stepper motors physically interface with the microscope's stage knobs and focus mechanisms—replicating human movement to scan the entire slide grid smoothly without touching or altering the original hardware.
- **The Brain:** An edge-optimized Deep Learning model classifies fields under Bethesda System criteria (NILM, LSIL, HSIL) and isolates suspicious regions instantly.

### ⚙️ System Architecture & Tech Stack

#### 🖥️ Edge Computing & GUI (`Raspberry Pi 5`)
- **Core Unit:** Raspberry Pi 5 (8GB RAM) with a 7" touchscreen.
- **Software Stack:** Developed in Python (`Tkinter` + `OpenCV` + `TensorFlow`), optimized with multi-threading and graph compilation caching.
- **Biological Pre-filters:** Evaluates sharpness (Laplacian variance) and cellular content (HSV masks and Otsu thresholding) before running inference, discarding empty or blurry fields automatically.

#### 🦾 Mechatronics & Hardware Control (`ESP32-C3 Mini`)
- **Microcontroller:** ESP32-C3 Mini managing precise step execution via serial USB communication (`/dev/ttyACM0`).
- **Motion System:** Dual NEMA 17 stepper motors for the Y-axis (with follower synchronization) and X-axis motion, navigated via an analog joystick override or automated scanning loops.

---

## 🇲🇽 VERSIÓN EN ESPAÑOL

### 💡 El Problema
En zonas con alta incidencia de cáncer cervicouterino y pocos recursos, el personal médico se enfrenta a un cuello de botella brutal: **analizar miles de laminillas de Papanicolaou de forma manual**. Hasta el 98% de las muestras resultan negativas (NILM), pero revisarlas una por una genera fatiga visual severa en los citotecnólogos, retrasos en la entrega de resultados y, en el peor de los casos, diagnósticos tardíos.

### 🚀 ¿Qué es SOVIC?
**SOVIC** es un equipo de escaneo y triaje automatizado de bajo costo para puntos de atención (*Point-of-Care*). 

En lugar de modificar los microscopios tradicionales o requerir costosos equipos industriales, SOVIC replica la destreza y la visión humana de forma totalmente no invasiva:
- **Los Ojos:** Una cámara universal para microscopio acoplada al ocular captura los campos ópticos en tiempo real.
- **Las Manos y Dedos:** Un sistema mecánico con adaptadores impresos en 3D, bandas dentadas y motores paso a paso NEMA 17 se acopla a las perillas y ejes del microscopio, moviendo la platina con precisión milimétrica para recorrer toda la muestra de manera automatizada.
- **El Cerebro:** Un modelo de Deep Learning optimizado corre localmente para clasificar los campos bajo los criterios del Sistema Bethesda (NILM, LSIL, HSIL) y aislar las zonas sospechosas para que el especialista las revise directamente.

### ⚙️ Arquitectura del Sistema y Componentes

#### 🖥️ Interfaz y Procesamiento (`Raspberry Pi 5`)
- **Hardware:** Raspberry Pi 5 (8GB de RAM) con pantalla táctil de 7 pulgadas.
- **Software:** Aplicación de escritorio desarrollada en Python (`Tkinter` + `OpenCV` + `TensorFlow`), optimizada con manejo de hilos y precalentamiento de grafos para evitar latencias.
- **Pre-filtros biológicos:** El sistema evalúa la nitidez (Varianza de Laplaciano) y el contenido celular (máscaras HSV y umbralización de Otsu) antes de correr la inferencia, evitando analizar campos vacíos o con tejido apelmazado.

#### 🦾 Control Mecatrónico (`ESP32-C3 Mini`)
- **Microcontrolador:** ESP32-C3 Mini encargado de la ejecución de pasos mediante comunicación serial USB (`/dev/ttyACM0`).
- **Tracción:** Motores NEMA 17 controlados por hardware para el desplazamiento en ejes X/Y (con sincronización de motores gemelos en Y), permitiendo control manual por joystick o rutas automatizadas en rejilla.

---

## 📷 System Gallery / Galería del Sistema

### Physical Mounting / Montaje Físico sobre el Microscopio
<p align="center">
  <img src="assets/SOVIC_montado_1.jpeg" width="48%" alt="Side view">
  <img src="assets/SOVIC_montado_2.jpeg" width="48%" alt="Screen detail and connections">
</p>
<p align="center"><em>Mechatronic integration: motors coupled to microscope knobs, universal camera, and Raspberry Pi 5 in operation. / Integración mecatrónica: motores acoplados a las perillas, cámara universal y Raspberry Pi 5 en operación.</em></p>

---

### Touch Interface (GUI v8.1) / Interfaz Táctil
| Main Operation View / Vista Principal | System Connections / Conexiones del Sistema |
| :---: | :---: |
| <img src="assets/UI_1.png" width="100%" alt="Main UI"> | <img src="assets/UI_conexiones.png" width="100%" alt="Connections UI"> |

| Sample Explorer / Explorador de Muestras | Saved Folders Management / Gestión de Archivos |
| :---: | :---: |
| <img src="assets/carpetas_guardadas.png" width="100%" alt="Saved folders"> | <img src="assets/carpeta_muestras_guardadas.png" width="100%" alt="Sample explorer"> |

---

### Computer Vision Pipeline / Pipeline de Visión por Computadora

* **Chromatic Standardization (Reinhard) / Normalización Cromática:** Standardizes staining brightness and illumination to prevent bias across different laboratories. *(Estandariza la iluminación y el brillo de las tinciones para evitar sesgos entre laboratorios).*
  <p align="center">
    <img src="assets/figura_reinhard.png" width="85%" alt="Reinhard Normalization">
  </p>

* **Segmentation & Safe Crop / Segmentación y Recorte Seguro:** Isolates cellular components of interest while discarding slide background artifacts. *(Aisla los componentes celulares de interés descartando el fondo blanco del portaobjetos).*
  <p align="center">
    <img src="assets/figura_segmentacion.png" width="85%" alt="Segmentation and Masks">
  </p>

---
