# 🏎️ RR-Engineer: OBD-II Diagnostic System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Interface: PyQt5](https://img.shields.io/badge/UI-PyQt5-orange.svg)](https://pypi.org/project/PyQt5/)

**RR-Engineer** es una potente herramienta de diagnóstico automotriz desarrollada en Python. Permite monitorear el rendimiento del motor en tiempo real, leer códigos de falla (DTC) y verificar el estado de las emisiones del vehículo utilizando un adaptador **ELM327**.

---

## 🚀 Características Principales

- **📈 Dashboard en Tiempo Real**: Visualización de RPM, velocidad, temperaturas, voltajes y consumos.
- **🔧 Escáner DTC Profesional**: Identifica códigos de error (P, C, B, U) con descripciones técnicas detalladas.
- **❄️ Freeze Frame**: Captura el estado de los sensores en el momento exacto en que ocurrió una falla.
- **☁️ Monitor de Emisiones**: Verificación de preparación para pruebas de SMOG.
- **🚗 Gestión de Flota**: Registra múltiples vehículos (Marca, Modelo, Año) y guarda sus perfiles.
- **🎨 Interfaz Moderna**: Tema oscuro optimizado (Dark Mode) con estilos QSS profesionales.

---

## 🛠️ Requisitos de Hardware

Para usar este software con un vehículo real, necesitarás:
1.  **Adaptador OBD-II**: Compatible con **ELM327** (Bluetooth, USB o Wi-Fi con puerto COM virtual).
2.  **Computadora**: Con Windows/Linux/Mac y puerto USB o conexión Bluetooth.

---

## 📦 Instalación

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/tu-usuario/RR-OBD2.git
    cd RR-OBD2
    ```

2.  **Instala las dependencias:**
    ```bash
    pip install PyQt5 pyqtgraph pyserial
    ```

---

## ⚙️ Configuración y Uso

### 1. Conexión del Hardware
- Conecta el adaptador ELM327 al puerto OBD-II de tu vehículo (usualmente debajo del volante).
- Pon el auto en **ON** (ignición encendida) o arranca el motor.
- Si es Bluetooth, emparéjalo con tu PC primero.

### 2. Configuración en el Software
- Ejecuta la aplicación: `python rr_v5.py`.
- **Registro Inicial**: Al abrirlo por primera vez, registra la marca, modelo y año de tu auto.
- **Selección de Puerto**: En la parte superior, selecciona el puerto COM correspondiente a tu adaptador (ej. `COM4` o `/dev/ttyUSB0`).
- **Baud Rate**: Generalmente es `38400` para adaptadores antiguos o `115200` para los modernos. Si no conecta, intenta con ambos.
- Haz clic en **CONECTAR**. El LED cambiará a verde si la comunicación es exitosa.

### 3. Navegación
- Usa la **barra lateral** para cambiar entre el Dashboard, el Escáner de Fallas y los Ajustes.

---

## 📂 Estructura del Proyecto

- `rr_v5.py`: Archivo principal de la aplicación.
- `dtc_codes.json`: Base de datos extendida con miles de códigos de error.
- `styles.qss`: Hoja de estilos para la apariencia visual.
- `preferences.json`: Almacena tus vehículos y configuración activa.

---

## 🔧 Solución de Problemas

- **"No se encuentra el dispositivo"**: Verifica que los drivers del adaptador estén instalados y que el puerto COM sea el correcto en el Administrador de Dispositivos.
- **"Error de Lectura"**: Asegúrate de que el motor esté encendido o en posición ON. Algunos vehículos bloquean el bus de datos si están en OFF.
- **"Datos en 0"**: Algunos protocolos OBD-II tardan unos segundos en inicializar. Espera a que el Log muestre "CONEXIÓN COMPLETA".

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.
