import sys
import serial
import serial.tools.list_ports
import time
import csv
import json
import uuid
from datetime import datetime
import pyqtgraph as pg
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QGridLayout,
                             QFrame, QTextEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QStackedWidget, QScrollArea,
                             QComboBox, QListWidget, QDialog, QSpinBox, QLineEdit,
                             QSizePolicy)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QIcon
import os
import re

# --- CONFIGURACIÓN ---
# PUERTO_OBD se define ahora dinámicamente

# --- ESTILOS "PRO" ---
ESTILO_CSS = """
QMainWindow { background-color: #121212; }
QLabel { color: #e0e0e0; font-family: 'Segoe UI'; }
QPushButton { 
    background-color: #333; color: white; border: 1px solid #444; 
    padding: 15px; border-radius: 8px; font-weight: bold; font-size: 16px;
}
QPushButton:hover { background-color: #007acc; border-color: #00aaff; }
QPushButton:pressed { background-color: #005f99; }
QFrame { background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333; }
QTableWidget { 
    background-color: #1e1e1e; gridline-color: #333; color: #ddd; border: none; font-size: 14px;
}
QHeaderView::section { 
    background-color: #252526; color: #00aaff; padding: 8px; border: none; font-weight: bold;
}
QTextEdit { background-color: #1e1e1e; color: #0f0; font-family: 'Consolas'; border: 1px solid #333; }
/* Estilos específicos para tarjetas de dashboard */
QLabel#DashboardValue { font-size: 36px; color: #00e5ff; font-weight: bold; }
QLabel#DashboardUnit { font-size: 14px; color: #888; }
QLabel#DashboardTitle { font-size: 14px; color: #ccc; font-weight: 600; text-transform: uppercase; }
/* Estilos para estado de monitores */
QLabel#MonitorOK { color: #00e676; font-weight: bold; }
QLabel#MonitorInc { color: #ffeb3b; font-weight: bold; }
QLabel#MonitorFail { color: #ff1744; font-weight: bold; }
/* Combos en header */
QComboBox { 
    background-color: #333; color: white; border: 1px solid #555; padding: 5px; font-size: 14px;
}
"""




# ─── VEHICLE MANAGER ────────────────────────────────────────────────────────

class VehicleManager:
    """Gestiona vehículos guardados en preferences.json"""

    def __init__(self, script_dir):
        self.prefs_path = os.path.join(script_dir, "preferences.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.prefs_path):
            try:
                with open(self.prefs_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"vehicles": [], "active_vehicle_id": None}

    def save(self):
        try:
            with open(self.prefs_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando preferencias: {e}")

    def add_vehicle(self, brand, model, year):
        vid = str(uuid.uuid4())[:8]
        vehicle = {"id": vid, "brand": brand, "model": model, "year": year}
        self.data["vehicles"].append(vehicle)
        if not self.data["active_vehicle_id"]:
            self.data["active_vehicle_id"] = vid
        self.save()
        return vehicle

    def remove_vehicle(self, vid):
        self.data["vehicles"] = [v for v in self.data["vehicles"] if v["id"] != vid]
        if self.data["active_vehicle_id"] == vid:
            self.data["active_vehicle_id"] = (
                self.data["vehicles"][0]["id"] if self.data["vehicles"] else None
            )
        self.save()

    def set_active(self, vid):
        self.data["active_vehicle_id"] = vid
        self.save()

    def get_active(self):
        for v in self.data["vehicles"]:
            if v["id"] == self.data["active_vehicle_id"]:
                return v
        return None

    def get_by_id(self, vid):
        for v in self.data["vehicles"]:
            if v["id"] == vid:
                return v
        return None

    def get_all(self):
        return self.data["vehicles"]

    def has_vehicles(self):
        return len(self.data["vehicles"]) > 0

    @staticmethod
    def display_name(v):
        return f"{v['brand']} {v['model']} {v['year']}"


# ─── DIALOGS DE VEHÍCULO ─────────────────────────────────────────────────────

class VehicleSetupDialog(QDialog):
    """Diálogo para registrar/agregar un vehículo (Marca / Modelo / Año)."""

    MARCAS = [
        "Toyota", "Chevrolet", "Nissan", "Honda", "KIA", "Hyundai", "Ford",
        "Volkswagen", "Mazda", "Mitsubishi", "Suzuki", "Subaru", "BMW",
        "Mercedes-Benz", "Audi", "Jeep", "RAM", "Dodge", "Chrysler",
        "Isuzu", "SEAT", "Renault", "Peugeot", "Fiat", "Otra"
    ]

    def __init__(self, parent=None, title="Registrar Vehículo"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(450, 390)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 25, 35, 25)
        layout.setSpacing(10)

        lbl_icon = QLabel("🚗")
        lbl_icon.setStyleSheet("font-size: 38px;")
        lbl_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_icon)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 17px; font-weight: bold; color: #00e5ff;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_sub = QLabel("Ingresa los datos de tu vehículo para comenzar")
        lbl_sub.setStyleSheet("color: #777; font-size: 11px;")
        lbl_sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_sub)

        # ── Formulario ──
        form = QVBoxLayout()
        form.setSpacing(6)

        form.addWidget(self._lbl("Marca:"))
        self.combo_brand = QComboBox()
        self.combo_brand.addItems(self.MARCAS)
        self.combo_brand.setEditable(True)
        self.combo_brand.setMinimumHeight(34)
        form.addWidget(self.combo_brand)

        form.addWidget(self._lbl("Modelo:"))
        self.txt_model = QLineEdit()
        self.txt_model.setPlaceholderText("Ej: Corolla, Aveo, Sentra, Camry...")
        self.txt_model.setMinimumHeight(34)
        form.addWidget(self.txt_model)

        form.addWidget(self._lbl("Año:"))
        self.spin_year = QSpinBox()
        self.spin_year.setRange(1990, 2030)
        self.spin_year.setValue(2020)
        self.spin_year.setMinimumHeight(34)
        form.addWidget(self.spin_year)

        layout.addLayout(form)
        layout.addStretch()

        # ── Botones ──
        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setMinimumHeight(36)
        self.btn_save = QPushButton("💾  Guardar vehículo")
        self.btn_save.setMinimumHeight(36)
        self.btn_save.setStyleSheet(
            "background-color:#007acc; color:white; font-size:13px;"
            " font-weight:bold; border-radius:7px;"
        )
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

        self.btn_save.clicked.connect(self._on_save)
        self.btn_cancel.clicked.connect(self.reject)

    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet("color:#bbb; font-size:12px; font-weight:bold; margin-top:4px;")
        return l

    def _on_save(self):
        if not self.txt_model.text().strip():
            self.txt_model.setStyleSheet("border:1px solid #ff5555;")
            self.txt_model.setPlaceholderText("⚠ Ingresa el modelo del vehículo")
            return
        self.accept()

    def get_data(self):
        return {
            "brand": self.combo_brand.currentText().strip(),
            "model": self.txt_model.text().strip(),
            "year": self.spin_year.value()
        }


class VehicleSelectDialog(QDialog):
    """Diálogo para elegir qué vehículo escanear."""

    def __init__(self, vehicles, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Vehículo")
        self.setFixedSize(400, 210)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(14)

        lbl = QLabel("🚗  ¿Qué vehículo deseas escanear?")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #00e5ff;")
        layout.addWidget(lbl)

        self.combo = QComboBox()
        self.combo.setMinimumHeight(36)
        for v in vehicles:
            self.combo.addItem(VehicleManager.display_name(v), v["id"])
        layout.addWidget(self.combo)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setMinimumHeight(36)
        btn_scan = QPushButton("🔍  Escanear este vehículo")
        btn_scan.setMinimumHeight(36)
        btn_scan.setStyleSheet(
            "background-color:#d32f2f; color:white; font-weight:bold;"
            " font-size:13px; border-radius:7px;"
        )
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_scan)
        layout.addLayout(btn_row)

        btn_scan.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

    def selected_vehicle_id(self):
        return self.combo.currentData()


# ─── HILO OBD ────────────────────────────────────────────────────────────────

class HiloOBD(QThread):
    # Señales Sensor y Cálculos
    dato_sensor = pyqtSignal(str, float, str)
    datos_calculados = pyqtSignal(dict) # Para MPG, Distancia, etc.
    
    # Señales Diagnóstico
    nuevo_dtc = pyqtSignal(list, str)
    estado_emisiones = pyqtSignal(dict)
    nuevo_freeze_frame = pyqtSignal(dict) # Nueva señal
    
    # Señales Sistema
    log = pyqtSignal(str)
    conexion = pyqtSignal(bool)
    fin_escaneo = pyqtSignal() 

    def __init__(self):
        super().__init__()
        self.corriendo = True
        self.solicitud_dtc = False
        self.solicitud_emisiones = False
        self.ser = None
        
        # Estado Conexión
        self.port_target = None
        self.baud_target = None
        self.req_conectar = False
        self.req_desconectar = False

        # Variables para cálculos acumulativos
        self.distancia_km = 0.0
        self.combustible_litros = 0.0
        self.tiempo_inicio = 0
        self.last_update_time = 0
        self.velocidad_actual = 0
        self.maf_actual = 0 # Mass Air Flow (g/s)
        self.rpm_actual = 0
        self.in_dashboard = True

    def conectar(self, port, baud):
        self.port_target = port
        self.baud_target = baud
        self.req_conectar = True

    def desconectar(self):
        self.req_desconectar = True

    def run(self):
        self.tiempo_inicio = time.time()
        self.last_update_time = self.tiempo_inicio
        
        while self.corriendo:
            # GESTIÓN DE CONEXIÓN
            if self.req_conectar:
                self.req_conectar = False
                self.intentar_conexion()

            if self.req_desconectar:
                self.req_desconectar = False
                if self.ser: 
                    self.ser.close()
                    self.ser = None
                self.conexion.emit(False)
                self.log.emit("🔌 Desconectado manualmente.")

            # SI ESTÁ CONECTADO, EJECUTAR BUCLE DE CONFIGURACIÓN
            if self.ser and self.ser.is_open:
                try:
                    # 1. ESCANEOS BAJO DEMANDA
                    if self.solicitud_dtc:
                        self.ejecutar_escaneo_dtc()
                        self.solicitud_dtc = False
                        self.fin_escaneo.emit()
                    
                    elif self.solicitud_emisiones:
                        self.ejecutar_emisiones()
                        self.solicitud_emisiones = False
                    
                    else:
                        # 2. LECTURA DE SENSORES (Default)
                        if self.in_dashboard:
                             self.leer_sensores_reales()
                    
                    # 3. CÁLCULOS
                    self.calcular_derivados()

                except Exception as e:
                    self.log.emit(f"❌ Error IO: {e}")
                    self.conexion.emit(False)
                    if self.ser: self.ser.close()
                    self.ser = None
            else:
                # Si no está conectado, dormir para no consumir CPU
                time.sleep(0.1)

    def intentar_conexion(self):
        p = self.port_target
        b = self.baud_target
        self.log.emit(f"━━━ DIAGNÓSTICO DE CONEXIÓN ━━━")
        self.log.emit(f"Puerto: {p}")
        self.log.emit(f"Velocidad: {b} baud")
        
        try:
            # PASO 1: Abrir puerto
            self.log.emit("PASO 1: Abriendo puerto serial...")
            self.ser = serial.Serial(
                port=p, 
                baudrate=b, 
                timeout=2.0, 
                write_timeout=2.0,
                xonxoff=False,
                rtscts=False
            )
            self.log.emit(f"✓ Puerto abierto OK (timeout={self.ser.timeout}s)")
            
            # PASO 2: Despertar el ELM
            self.log.emit("PASO 2: Enviando WAKE-UP...")
            time.sleep(0.3)
            self.ser.write(b"ATZ\r")
            time.sleep(1.5)  # Esperar reset
            
            # PASO 3: Leer respuesta
            self.log.emit("PASO 3: Leyendo respuesta...")
            resp = self.ser.read(200).decode(errors='ignore').strip()
            self.log.emit(f"RESPUESTA RAW ({len(resp)} bytes):")
            self.log.emit(f"  '{resp}'")
            
            # PASO 4: Validar
            if len(resp) >= 2:
                self.log.emit("✅ ¡DISPOSITIVO RESPONDE!")
                self.log.emit("PASO 4: Inicializando protocolo...")
                self.inicializar_obd()
                self.conexion.emit(True)
                self.log.emit("━━━ CONEXIÓN COMPLETA ━━━")
            else:
                self.log.emit("⚠️ DISPOSITIVO NO RESPONDE")
                self.log.emit("   Posibles causas:")
                self.log.emit("   - Adaptador apagado")
                self.log.emit("   - Baud rate incorrecto")
                self.log.emit("   - Cable desconectado")
                self.ser.close()
                self.ser = None
                self.conexion.emit(False)

        except serial.SerialException as e:
            self.log.emit(f"❌ ERROR DE PUERTO: {e}")
            self.log.emit("   ¿El puerto está en uso por otro programa?")
            if self.ser: self.ser.close()
            self.ser = None
            self.conexion.emit(False)
        except Exception as e:
            self.log.emit(f"❌ ERROR GENERAL: {e}")
            if self.ser: self.ser.close()
            self.ser = None
            self.conexion.emit(False)

    def inicializar_obd(self):
        cmds = ["AT Z", "AT E0", "AT SP 0", "AT ST 64", "AT S0"]
        for c in cmds:
            self.enviar_raw(c)
            time.sleep(0.1)

    def enviar_raw(self, cmd):
        if not self.ser: return ""
        try:
            # self.ser.reset_input_buffer() # Eliminado por seguridad
            self.ser.write((cmd + "\r").encode())
            resp = self.ser.read_until(b'>').decode(errors='ignore').strip()
            self.log.emit(f"TX: {cmd} -> RX: {resp}") 
            return resp
        except Exception as e:
            self.log.emit(f"ErrTX: {e}") 
            return ""

    def leer_sensores_reales(self):
        # PID 01 0C: RPM
        val = self.consultar_pid("01 0C", lambda x: int(x, 16)/4)
        if val is not None: 
            self.rpm_actual = val
            self.dato_sensor.emit("RPM", val, f"{val:.0f}")
        time.sleep(0.1)  # Delay para no saturar el bus

        # PID 01 0D: Velocidad
        val = self.consultar_pid("01 0D", lambda x: int(x, 16))
        if val is not None: 
            self.velocidad_actual = val
            self.dato_sensor.emit("VEL", val, f"{val:.0f}")
        time.sleep(0.1)
        
        # PID 01 05: ECT
        self.consultar_y_emitir("01 05", "ECT", lambda x: int(x, 16)-40, "°C")
        time.sleep(0.1)
        
        # PID 01 10: MAF
        val = self.consultar_pid("01 10", lambda x: int(x, 16)/100)
        if val is not None:
            self.maf_actual = val
            self.dato_sensor.emit("MAF", val, f"{val:.2f}")

        # PID 01 0B: MAP (Siempre consultar por separado)
        val_map = self.consultar_pid("01 0B", lambda x: int(x, 16))
        if val_map is not None:
            self.dato_sensor.emit("MAP", val_map, f"{val_map}")
            # Si no hay MAF, estimar para consumo (maf = map * rpm / temp...) - Opcional complejo
            if self.maf_actual == 0:
                 # Estimación muy burda para que el consumo no sea 0 si hay MAP
                 # MAF_g_s ~= (RPM * MAP / 120) * Eficiencia Volumetrica (aprox 80% o 0.8) * Cilindrada L (aprox 2L)
                 if self.rpm_actual > 0:
                     # Fórmula simplificada MAF estimativo: MAF = (RPM * MAP / 120) * 0.85 (para un motor 2.0L aprox)
                     maf_est = (self.rpm_actual * val_map / 120.0) * 0.85
                     self.maf_actual = maf_est
                     self.dato_sensor.emit("MAF", maf_est, f"{maf_est:.2f} (Est)")


        # PID 01 04: Carga Motor
        self.consultar_y_emitir("01 04", "LOAD", lambda x: int(x, 16)/2.55, "%")
        time.sleep(0.05)

        # PID 01 11: Throttle
        self.consultar_y_emitir("01 11", "THROTTLE", lambda x: int(x, 16)/2.55, "%")
        time.sleep(0.05)

        # PID 01 06: Fuel Trim (Short Term Bank 1)
        self.consultar_y_emitir("01 06", "FUEL_TRIM", lambda x: (int(x, 16)-128) * 100/128, "%")
        time.sleep(0.05)

        # --- NUEVOS SENSORES ---
        
        # PID 01 0E: Timing Advance
        self.consultar_y_emitir("01 0E", "TIMING", lambda x: (int(x, 16)-128)/2, "°")
        time.sleep(0.05)

        # PID 01 0F: Intake Air Temperature (IAT)
        self.consultar_y_emitir("01 0F", "IAT", lambda x: int(x, 16)-40, "°C")
        time.sleep(0.05)

        # PID 01 14: O2 Sensor Bank 1 Sensor 1 (Voltaje - Narrowband)
        # Retorna 2 bytes: A (Voltaje), B (Fuel Trim)
        val_o2 = self.consultar_pid("01 14", lambda h: int(h[0:2], 16)/200 if len(h)>=2 else 0)
        if val_o2 is not None:
             self.dato_sensor.emit("O2", val_o2, f"{val_o2:.3f}")
        else:
             # Fallback: Wideband Lambda (PID 01 24)
             # Retorna 4 bytes (A,B,C,D). Lambda = ((A*256)+B)*2/65536
             val_lambda = self.consultar_pid("01 24", lambda h: ((int(h[0:2], 16)*256)+int(h[2:4], 16))*2/65536 if len(h)>=4 else 1.0)
             if val_lambda is not None:
                 self.dato_sensor.emit("O2_WR", val_lambda, f"λ {val_lambda:.3f}")
        time.sleep(0.05)

        # Voltaje (AT RV)
        try:
            volt_raw = self.enviar_raw("AT RV")
            # Buscar patrón decimal como 12.8 o 14.1
            m = re.search(r"([0-9]+\.[0-9]+)", volt_raw)
            if m:
                val = float(m.group(1))
                self.dato_sensor.emit("VOLT", val, f"{val:.1f}")
        except: pass
        time.sleep(0.05)

    def consultar_pid(self, pid, formula):
        try:
            raw = self.enviar_raw(pid)
            # Normalizar: quitar espacios, > y saltos de línea
            clean_raw = raw.replace(" ", "").replace(">", "").replace("\r", "").replace("\n", "")
            
            # Buscar el eco positivo del servicio + PID. Ej: Modo 01 PID 0C -> Busca 410C
            mode_pid = pid.split()
            modo_respuesta = int(mode_pid[0], 16) + 0x40 # "01" -> 0x41, "02" -> 0x42
            target = f"{modo_respuesta:02X}{mode_pid[1]}" # EJ: 410C o 420C
            
            if target in clean_raw: 
                # Extraer todo lo que sigue al target
                payload = clean_raw.split(target)[-1]
                # Tomamos solo la longitud esperada hex (opcional, pero seguro)
                # Si llega basura al final, el try-except lo maneja
                if len(payload) >= 2: 
                    return formula(payload)
            else:
                 if "NODATA" not in clean_raw and len(clean_raw) > 0:
                     self.log.emit(f"⚠️ PID {pid} INVALIDO: '{raw}'")
        except Exception as e: 
            self.log.emit(f"ErrPID {pid}: {e}")
            return None
        return None

    def consultar_y_emitir(self, pid, clave, formula, unidad=""):
        val = self.consultar_pid(pid, formula)
        if val is not None:
            self.dato_sensor.emit(clave, val, f"{val:.1f}")

    def calcular_derivados(self):
        if not self.ser or not self.ser.is_open: return 
        
        now = time.time()
        dt = now - self.last_update_time
        self.last_update_time = now

        if self.velocidad_actual > 0:
            dist_delta = (self.velocidad_actual * (dt / 3600.0))
            self.distancia_km += dist_delta

        if self.maf_actual > 0:
            litros_delta = (self.maf_actual * dt) / (14.7 * 740)
            self.combustible_litros += litros_delta
        
        kml_inst = 0
        if self.maf_actual > 0:
            kml_inst = self.velocidad_actual / (self.maf_actual * 0.33)

        tiempo_total_h = (now - self.tiempo_inicio) / 3600.0
        vel_media = self.distancia_km / tiempo_total_h if tiempo_total_h > 0 else 0

        datos = {
            "DISTANCIA": f"{self.distancia_km:.2f}",
            "COMBUSTIBLE": f"{self.combustible_litros:.3f}",
            "KML_INST": f"{kml_inst:.1f}",
            "VEL_MEDIA": f"{vel_media:.1f}"
        }
        self.datos_calculados.emit(datos)

    def ejecutar_escaneo_dtc(self):
        self.log.emit("🔍 Iniciando Escaneo REAL (Modo $03)...")
        time.sleep(0.5)
        
        codes = []
        raw_response = self.enviar_raw("03")
        self.log.emit(f"RAW DTC: '{raw_response}'") 

        try:
            clean_hex = ""
            lines = raw_response.split('\r')
            for line in lines:
                line = line.replace(">", "").strip()
                if ":" in line:
                    parts = line.split(":")
                    if len(parts) > 1: line = parts[1]
                clean_hex += line.replace(" ", "")

            # Ahora buscamos la respuesta '43'
            if "43" in clean_hex:
                idx = clean_hex.find("43") + 2
                payload = clean_hex[idx:]
                
                # REGLA IMPORTANTE: Los DTC son de 2 bytes (4 caracteres HEX).
                # Si el payload tiene longitud impar de bytes (ej: 6 chars = 3 bytes), 
                # el primer byte suele ser la CANTIDAD de códigos.
                if len(payload) % 4 != 0:
                    # Sobra un byte (2 caracteres), asumimos que es el contador al inicio
                    self.log.emit(f"Info: Saltando byte de conteo '{payload[:2]}'")
                    payload = payload[2:]

                # Procesar en bloques de 4 caracteres (2 bytes)
                for i in range(0, len(payload), 4):
                    chunk = payload[i:i+4]
                    if len(chunk) == 4:
                        if chunk == "0000": continue 
                        try:
                            a = int(chunk[0:2], 16)
                            b = int(chunk[2:4], 16)
                            
                            type_bits = (a & 0xC0) >> 6
                            prefix = ["P", "C", "B", "U"][type_bits]
                            
                            digit1 = (a & 0x30) >> 4
                            digit2 = (a & 0x0F)
                            
                            code_num = f"{digit1}{digit2:X}{b:02X}"
                            full_code = f"{prefix}{code_num}"
                            codes.append(full_code)
                        except:
                            codes.append(f"UNK-{chunk}")
        except Exception as e:
            self.log.emit(f"Error parseando: {e}")
            codes.append("ERR-PARSE")

        # Intentar leer Freeze Frame si hay códigos
        ff_data = None
        if codes and "ERR-PARSE" not in codes:
             self.log.emit("📸 Buscando Freeze Frame (Datos congelados)...")
             ff_data = self.get_freeze_frame()

        self.nuevo_dtc.emit(codes, raw_response)
        # Emitimos señal extra o reutilizamos la misma (tú decides, aquí emito log por ahora)
        if ff_data:
            self.log.emit(f"❄️ FREEZE FRAME DETECTADO: {ff_data}")
            # Idealmente emitir esto a la UI, por simplicidad lo pegaré al raw_response o crearé señal nueva.
            # Para no romper compatibilidad, modificaré la firma de la señal nuevo_dtc en __init__
            # Pero eso requiere cambiar todos los connects.
            # Mejor opción: Agregar al final de la lista de codigos un elemento especial o usar otra señal.
            # Voy a usar una señal nueva en HiloOBD.

    def get_freeze_frame(self):
        # Implementación básica de lectura de Freeze Frame (Modo 02)
        # Por ahora intentaremos leer algunos PIDs clave en el momento de falla
        ff_data = {}
        try:
            # PID 02 0C: RPM en Freeze Frame
            val = self.consultar_pid("02 0C 00", lambda x: int(x, 16)/4)
            if val is not None: ff_data["RPM"] = f"{val:.0f}"
            
            # PID 02 0D: Velocidad
            val = self.consultar_pid("02 0D 00", lambda x: int(x, 16))
            if val is not None: ff_data["VEL"] = f"{val} km/h"
            
            # PID 02 05: ECT
            val = self.consultar_pid("02 05 00", lambda x: int(x, 16)-40)
            if val is not None: ff_data["ECT"] = f"{val} °C"
            
            # PID 02 04: Carga
            val = self.consultar_pid("02 04 00", lambda x: int(x, 16)/2.55)
            if val is not None: ff_data["LOAD"] = f"{val:.1f} %"
            
        except Exception as e:
            self.log.emit(f"Error Freeze Frame: {e}")
            
        return ff_data

    def ejecutar_emisiones(self):
        self.log.emit("📋 Verificando Monitores (Iso 15765-4 CAN)...")
        res = {}
        try:
            raw = self.enviar_raw("01 01")
            self.log.emit(f"EMISIONES RAW: '{raw}'")
            
            clean_raw = raw.replace(" ", "").replace(">", "")
            import re
            matches = re.findall(r"4101([0-9A-Fa-f]{8})", clean_raw)
            
            best_payload = None
            max_supported = -1

            # Buscamos la respuesta con más monitores soportados/completos
            if matches:
                for payload in matches:
                    # Analizamos qué tan "completa" es esta respuesta
                    # Si tiene muchos 00, probablemente es TCU o inválida
                    if payload == "00000000": continue
                    
                    B = int(payload[2:4], 16)
                    C = int(payload[4:6], 16)
                    
                    # Contamos bits en 1 en campos de soporte (para elegir la mejor ECU)
                    score = bin(B).count('1') + bin(C).count('1')
                    if score > max_supported:
                        max_supported = score
                        best_payload = payload
            
            if best_payload:
                self.log.emit(f"Usando respuesta ECU: {best_payload}")
                A = int(best_payload[0:2], 16)
                B = int(best_payload[2:4], 16)
                C = int(best_payload[4:6], 16)
                D = int(best_payload[6:8], 16)
                    
                # --- Interpretar BYTE A (MIL) ---
                mil_on = (A & 0x80) > 0
                res["MIL"] = "ON" if mil_on else "OFF"
                
                # Función auxiliar para determinar estado
                # Lógica: Si "Complete" (Bit X) es 1, entonces está OK (y por ende soportado)
                # Si "Supported" (Bit Y) es 1, verificamos "Complete"
                # Si ambos 0 -> N/A
                def check_status(supported, complete):
                    if complete: return "OK"
                    if supported: return "INC"
                    return "N/A"

                # --- Interpretar BYTE B (Monitores Continuos) ---
                # Misfire: Supp(4), Compl(0)
                res["Misfire"] = check_status(B&(1<<4), B&(1<<0))
                # Fuel: Supp(5), Compl(1)
                res["Fuel System"] = check_status(B&(1<<5), B&(1<<1))
                # Components: Supp(6), Compl(2)
                res["Components"] = check_status(B&(1<<6), B&(1<<2))

                # --- Interpretar BYTE C y D (Monitores No Continuos) ---
                # Catalyst: Supp(C0), Compl(D0)
                res["Catalyst"] = check_status(C&(1<<0), D&(1<<0))
                # Heated Cat: Supp(C1), Compl(D1)
                res["Heated Catalyst"] = check_status(C&(1<<1), D&(1<<1))
                # Evap: Supp(C2), Compl(D2)
                res["Evap"] = check_status(C&(1<<2), D&(1<<2))
                # Sec Air: Supp(C3), Compl(D3)
                res["Sec Air"] = check_status(C&(1<<3), D&(1<<3))
                # A/C: Supp(C4), Compl(D4)
                res["A/C"] = check_status(C&(1<<4), D&(1<<4))
                # O2 Sensor: Supp(C5), Compl(D5)
                res["O2 Sensor"] = check_status(C&(1<<5), D&(1<<5))
                # O2 Heater: Supp(C6), Compl(D6)
                res["O2 Heater"] = check_status(C&(1<<6), D&(1<<6))
                # EGR: Supp(C7), Compl(D7)
                res["EGR"] = check_status(C&(1<<7), D&(1<<7))

        except Exception as e:
            self.log.emit(f"Error decodificando emisiones: {e}")
            
        self.estado_emisiones.emit(res)

class MainMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("RR-Engineer")
        title.setStyleSheet("font-size: 40px; color: #00e5ff; font-weight: bold; margin-bottom: 30px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(20)

        # Botón 1: Dashboard
        self.btn_dash = self.create_big_button("🏎️\nDASHBOARD", "#00aaff")
        grid.addWidget(self.btn_dash, 0, 0)

        # Botón 2: Fallas
        self.btn_dtc = self.create_big_button("🔧\nFALLAS (DTC)", "#ff5555")
        grid.addWidget(self.btn_dtc, 0, 1)

        # Botón 3: Emisiones
        self.btn_emisiones = self.create_big_button("☁️\nEMISIONES", "#00e676")
        grid.addWidget(self.btn_emisiones, 0, 2)

        layout.addLayout(grid)

    def create_big_button(self, text, color_hover):
        btn = QPushButton(text)
        btn.setFixedSize(250, 200)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                font-size: 24px; background-color: #2d2d2d; 
                border: 2px solid #444; border-radius: 15px;
            }}
            QPushButton:hover {{ 
                background-color: {color_hover}; border-color: white; color: #111;
            }}
        """)
        return btn

class HeaderApp(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("HeaderFrame")
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.setSpacing(10)

        # Logo / Título
        lbl_title = QLabel("RR-Engineer")
        lbl_title.setStyleSheet("color: #00e5ff; font-size: 22px; font-weight: bold; letter-spacing: 2px;")
        layout.addWidget(lbl_title)

        # Label del vehículo activo
        self.lbl_vehicle = QLabel("")
        self.lbl_vehicle.setStyleSheet(
            "color: #00aaff; font-size: 12px; background-color: #1a2535;"
            " padding: 3px 10px; border-radius: 5px; border: 1px solid #00aaff44;"
        )
        layout.addWidget(self.lbl_vehicle)

        layout.addStretch()

        # Selector de Puerto
        layout.addWidget(QLabel("Puerto:"))
        self.combo_ports = QComboBox()
        self.combo_ports.setMinimumWidth(200)
        layout.addWidget(self.combo_ports)

        # Selector de Velocidad
        layout.addWidget(QLabel("Baud:"))
        self.combo_baud = QComboBox()
        self.combo_baud.addItems(["9600", "38400", "115200"])
        self.combo_baud.setCurrentText("115200")
        self.combo_baud.setFixedWidth(100)
        layout.addWidget(self.combo_baud)

        # Botón Conectar
        self.btn_connect = QPushButton("CONECTAR")
        self.btn_connect.setObjectName("ConnectButton")
        self.btn_connect.setFixedSize(130, 36)
        layout.addWidget(self.btn_connect)

        # Status LED
        self.status_led = QLabel()
        self.status_led.setFixedSize(18, 18)
        self.status_led.setStyleSheet("background-color: #ff1744; border-radius: 9px; border: 2px solid #b2102f;")
        layout.addWidget(self.status_led)

        # Texto Status
        self.lbl_status_text = QLabel("DESCONECTADO")
        self.lbl_status_text.setStyleSheet("color: #666; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.lbl_status_text)

        # Llenar puertos
        self.actualizar_puertos()

    def actualizar_puertos(self):
        self.combo_ports.clear()
        ports = serial.tools.list_ports.comports()
        if not ports:
            self.combo_ports.addItem("No se encontraron puertos")
        for p in ports:
            self.combo_ports.addItem(f"{p.device} - {p.description}")


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        # Layout exterior del widget: contiene el ScrollArea
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Scroll Area para evitar que las tarjetas se corten
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        outer_layout.addWidget(scroll)

        # Widget interior que contiene el grid
        inner_widget = QWidget()
        inner_widget.setStyleSheet("background: transparent;")
        scroll.setWidget(inner_widget)

        self.layout_grid = QGridLayout(inner_widget)
        self.layout_grid.setSpacing(15)
        self.layout_grid.setContentsMargins(10, 10, 10, 10)

        # Columnas con igual peso para distribución uniforme
        for col in range(3):
            self.layout_grid.setColumnStretch(col, 1)
        # Filas con igual peso
        for row in range(5):
            self.layout_grid.setRowStretch(row, 1)

        # Fila 0: Críticos
        self.rpm = self.add_card(self.layout_grid, "RPM MOTOR", "RPM", 0, 0)
        self.vel = self.add_card(self.layout_grid, "VELOCIDAD", "km/h", 0, 1)
        self.temp = self.add_card(self.layout_grid, "TEMP. REFRIG", "°C", 0, 2)
        
        # Fila 1: Carga y Combustible
        self.load = self.add_card(self.layout_grid, "CARGA MOTOR", "%", 1, 0)
        self.maf = self.add_card(self.layout_grid, "FLUJO AIRE (MAF)", "g/s", 1, 1)
        self.throttle = self.add_card(self.layout_grid, "ACELERADOR", "%", 1, 2)
        
        # Fila 2: Voltajes
        self.volt = self.add_card(self.layout_grid, "VOLTAJE BATERÍA", "V", 2, 0)
        self.fuel_trim = self.add_card(self.layout_grid, "CORRECCIÓN COMBUSTIBLE", "%", 2, 1)
        self.map_sensor = self.add_card(self.layout_grid, "PRESIÓN (MAP)", "kPa", 2, 2)
        
        # Fila 3: Calculados (Trip)
        self.dist = self.add_card(self.layout_grid, "DISTANCIA VIAJE", "km", 3, 0)
        self.fuel = self.add_card(self.layout_grid, "COMB. CONSUMIDO", "L", 3, 1)
        self.kml = self.add_card(self.layout_grid, "RENDIMIENTO INST.", "km/L", 3, 2)

        # Fila 4: Sensores Extra
        self.timing = self.add_card(self.layout_grid, "AVANCE TIEMPO", "°", 4, 0)
        self.iat = self.add_card(self.layout_grid, "TEMP. AIRE (IAT)", "°C", 4, 1)
        self.o2 = self.add_card(self.layout_grid, "SENSOR O2 (B1S1)", "V", 4, 2)

        # Gráfica Mini RPM (Sparkline)
        self.curve_rpm = None
        self.data_rpm = []
        # (Futura expansión para gráfica real)

    def add_card(self, layout, title, unit, row, col):
        frame = QFrame()
        frame.setObjectName("MetricCard") # CSS styling
        frame.setMinimumHeight(110)  # Altura mínima garantizada para cada tarjeta
        l = QVBoxLayout(frame)
        l.setContentsMargins(15, 12, 15, 12)
        l.setSpacing(4)
        
        lbl_t = QLabel(title)
        lbl_t.setObjectName("MetricTitle")
        lbl_t.setAlignment(Qt.AlignLeft)
        lbl_t.setWordWrap(True)  # Evita corte de texto largo
        
        lbl_v = QLabel("---")
        lbl_v.setObjectName("MetricValue")
        lbl_v.setAlignment(Qt.AlignCenter)
        
        lbl_u = QLabel(unit)
        lbl_u.setObjectName("MetricUnit")
        lbl_u.setAlignment(Qt.AlignRight)
        
        l.addWidget(lbl_t)
        l.addStretch(1)
        l.addWidget(lbl_v)
        l.addWidget(lbl_u)
        
        # Identificar tarjeta de temperatura
        if "TEMP" in title or unit == "°C":
             self.lbl_temp_status = QLabel("---")
             self.lbl_temp_status.setAlignment(Qt.AlignCenter)
             self.lbl_temp_status.setStyleSheet("color: #666; font-size: 12px;")
             l.addWidget(self.lbl_temp_status)
        
        layout.addWidget(frame, row, col)
        return lbl_v

    def update_val(self, key, val, text):
        if key == "RPM": 
            self.rpm.setText(text)
            self.data_rpm.append(float(val))
            if len(self.data_rpm) > 100: self.data_rpm.pop(0)
            if self.curve_rpm:
                self.curve_rpm.setData(self.data_rpm)
            
            # Color RPM
            try:
                rpm_val = float(val)
                if rpm_val > 5000: self.rpm.setStyleSheet("color: #ff1744; font-weight: bold;")
                else: self.rpm.setStyleSheet("color: #00e5ff; font-weight: bold;")
            except: pass
        
        elif key == "VEL": self.vel.setText(text)
        
        elif key == "ECT": 
            self.temp.setText(text)
            # Lógica de Alerta de Temperatura
            try:
                temp_val = float(val)
                if temp_val > 105: # Sobrecalentamiento
                    self.temp.setStyleSheet("color: #ff1744; font-size: 40px; font-weight: bold;") 
                    self.lbl_temp_status.setText(f"⚠️ ¡PELIGRO! >105°C\nRevisar Refrigerante")
                    self.lbl_temp_status.setStyleSheet("color: #ff1744; font-size: 12px; font-weight: bold;")
                elif temp_val < 80: # Frío
                    self.temp.setStyleSheet("color: #00e5ff; font-size: 40px; font-weight: bold;")
                    self.lbl_temp_status.setText("Motor Frío\n(Ideal: 85-95°C)")
                    self.lbl_temp_status.setStyleSheet("color: #00e5ff; font-size: 12px;")
                else: # Normal
                    self.temp.setStyleSheet("color: #00e676; font-size: 40px; font-weight: bold;")
                    self.lbl_temp_status.setText("Temperatura\nNormal (OK)")
                    self.lbl_temp_status.setStyleSheet("color: #00e676; font-size: 12px;")
            except: pass

        elif key == "LOAD": 
            self.load.setText(text)
            try:
                load_val = float(val)
                if load_val > 80: self.load.setStyleSheet("color: #ff1744; font-weight: bold;")
                else: self.load.setStyleSheet("color: #00e676; font-weight: bold;")
            except: pass

        elif key == "MAF": 
            self.maf.setText(text)
            self.maf.setStyleSheet("color: #00e5ff; font-weight: bold;")
            
        elif key == "MAP":
            self.map_sensor.setText(text)
            self.map_sensor.setStyleSheet("color: #ffeb3b; font-weight: bold;")

        elif key == "THROTTLE": self.throttle.setText(text)
        
        elif key == "VOLT": 
            self.volt.setText(text)
            try:
                volt_val = float(val)
                if volt_val < 12.0 or volt_val > 15.0:
                    self.volt.setStyleSheet("color: #ff1744; font-weight: bold;")
                else:
                    self.volt.setStyleSheet("color: #00e676; font-weight: bold;")
            except: pass

        elif key == "FUEL_TRIM": self.fuel_trim.setText(text)
        
        elif key == "TIMING": self.timing.setText(text)
        
        elif key == "IAT": 
            self.iat.setText(text)
            try:
                iat_val = float(val)
                if iat_val > 60: self.iat.setStyleSheet("color: #ff1744; font-weight: bold;")
                else: self.iat.setStyleSheet("color: #00e676; font-weight: bold;")
            except: pass

        elif key == "O2": 
            self.o2.setText(text)
            self.o2.setStyleSheet("color: #aa00ff; font-weight: bold;") # Morado neon
            
        elif key == "O2_WR": # Wideband Lambda
            self.o2.setText(text)
            try:
                lam = float(val)
                if 0.95 <= lam <= 1.05: # Ideal
                    self.o2.setStyleSheet("color: #00e676; font-weight: bold;")
                elif lam < 0.95: # Rico
                    self.o2.setStyleSheet("color: #00e5ff; font-weight: bold;") 
                else: # Pobre
                    self.o2.setStyleSheet("color: #ff1744; font-weight: bold;")
            except: pass

    def update_calc(self, data):
        self.dist.setText(data.get("DISTANCIA", "0.00"))
        self.fuel.setText(data.get("COMBUSTIBLE", "0.000"))
        self.kml.setText(data.get("KML_INST", "0.0"))

class DTCScreen(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Header ──────────────────────────────────────────────────────────
        h_row = QHBoxLayout()
        lbl_title = QLabel("🔍  ESCÁNER PROFESIONAL DE FALLAS")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0;")
        h_row.addWidget(lbl_title)

        self.lbl_vehicle_scanned = QLabel("")
        self.lbl_vehicle_scanned.setStyleSheet(
            "color:#00aaff; font-size:12px; background:#1a2535;"
            " padding:3px 10px; border-radius:5px; border:1px solid #00aaff44;"
        )
        self.lbl_vehicle_scanned.hide()
        h_row.addWidget(self.lbl_vehicle_scanned)
        h_row.addStretch()

        self.btn_scan = QPushButton("🔍  INICIAR DIAGNÓSTICO")
        self.btn_scan.setMinimumHeight(36)
        self.btn_scan.setStyleSheet("background-color:#c62828; color:white; font-weight:bold; padding:0 14px;")
        h_row.addWidget(self.btn_scan)
        layout.addLayout(h_row)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["CÓDIGO", "ESTADO", "DESCRIPCIÓN TÉCNICA"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Area de Freeze Frame
        lbl_ff = QLabel("❄️ DATOS CONGELADOS (Freeze Frame)")
        lbl_ff.setStyleSheet("color: #00e676; font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_ff)
        
        self.table_ff = QTableWidget()
        self.table_ff.setColumnCount(2)
        self.table_ff.setHorizontalHeaderLabels(["SENSOR", "VALOR AL MOMENTO DE LA FALLA"])
        self.table_ff.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_ff.setFixedHeight(150)
        layout.addWidget(self.table_ff)
        
        # Base de datos local ampliada
        self.dtc_db = {
            "P0300": "Fuego Perdido (Misfire) Aleatorio/Múltiple",
            "P0301": "Fuego Perdido Cilindro 1",
            "P0302": "Fuego Perdido Cilindro 2",
            "P0303": "Fuego Perdido Cilindro 3",
            "P0304": "Fuego Perdido Cilindro 4",
            "P0420": "Eficiencia Catalizador Baja (Banco 1)",
            "P0171": "Sistema Muy Pobre (Banco 1)",
            "P0172": "Sistema Muy Rico (Banco 1)",
            "P0113": "Sensor IAT Entrada Alta",
            "P0104": "Sensor MAF Circuito Intermitente",
            "P0204": "Inyector Cilindro 4 - Circuito Abierto/Corto",
            "P2004": "Control Corredor Admisión Atascado Abierto (Banco 1)",
            "C0943": "Falla sensor ángulo dirección (Posible)",
            "U0001": "Bus Comunicación CAN Alta Velocidad"
        }
        
        # Intentar cargar base de datos externa JSON
        try:
            import json
            import os
            
            # Buscar en el directorio actual
            json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dtc_codes.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    external_db = json.load(f)
                    self.dtc_db.update(external_db)
                    print(f"Cargados {len(external_db)} códigos extra desde dtc_codes.json")
        except Exception as e:
            print(f"No se pudo cargar dtc_codes.json: {e}")

    def mostrar_resultados(self, codigos, vehicle_name=""):
        self.table.setRowCount(0)
        self.table_ff.setRowCount(0)

        # Mostrar / ocultar badge de vehículo escaneado
        if vehicle_name:
            self.lbl_vehicle_scanned.setText(f"🚗  {vehicle_name}")
            self.lbl_vehicle_scanned.show()
        else:
            self.lbl_vehicle_scanned.hide()

        if not codigos:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem("—"))
            self.table.setItem(row, 1, QTableWidgetItem("SIN FALLAS"))
            self.table.item(row, 1).setForeground(QColor("#00e676"))
            self.table.setItem(row, 2, QTableWidgetItem("No se detectaron códigos de falla activos. ✅"))
            return

        for c in codigos:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Col 0: Código
            item_code = QTableWidgetItem(c.upper().strip())
            item_code.setForeground(QColor("#ff5555"))
            item_code.setFont(QFont("Segoe UI", 12, QFont.Bold))
            self.table.setItem(row, 0, item_code)

            # Col 1: Estado
            item_status = QTableWidgetItem("ACTIVO")
            item_status.setForeground(QColor("#ff5555"))
            self.table.setItem(row, 1, item_status)

            # Col 2: Descripción — normalizar código para evitar mismatch
            code_key = c.upper().strip()
            desc = self.dtc_db.get(code_key, f"Código {code_key} — Consulte manual de servicio")
            self.table.setItem(row, 2, QTableWidgetItem(desc))


    def mostrar_freeze_frame(self, data):
        self.table_ff.setRowCount(0)
        for k, v in data.items():
            row = self.table_ff.rowCount()
            self.table_ff.insertRow(row)
            self.table_ff.setItem(row, 0, QTableWidgetItem(k))
            self.table_ff.setItem(row, 1, QTableWidgetItem(str(v)))

class EmissionsScreen(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        h = QHBoxLayout()
        h.addWidget(QLabel("<h2>☁️ PRUEBAS DE EMISIONES Y SMOG</h2>"))
        self.btn_check = QPushButton("VERIFICAR MONITORES")
        self.btn_check.setStyleSheet("background-color: #00e676; color: #111;")
        h.addWidget(self.btn_check)
        layout.addLayout(h)
        
        self.grid = QGridLayout()
        layout.addLayout(self.grid)
        self.monitores = {}

        # Crear widgets para monitores predefinidos
        nombres = ["Misfire", "Fuel System", "Components", "Catalyst", "Evap", "O2 Sensor", "EGR", "Heated Catalyst"]
        for i, nombre in enumerate(nombres):
            frame = QFrame()
            l = QVBoxLayout(frame)
            l.addWidget(QLabel(nombre))
            
            lbl_status = QLabel("---")
            lbl_status.setAlignment(Qt.AlignCenter)
            lbl_status.setFont(QFont("Segoe UI", 18, QFont.Bold))
            l.addWidget(lbl_status)
            
            self.monitores[nombre] = lbl_status
            self.grid.addWidget(frame, i // 4, i % 4)
            
        layout.addStretch()

    def update_status(self, data):
        for k, v in data.items():
            if k in self.monitores:
                lbl = self.monitores[k]
                lbl.setText(v)
                if v == "OK": 
                    lbl.setStyleSheet("color: #00e676;") 
                elif v == "INC":
                    lbl.setStyleSheet("color: #ffeb3b;")
                else:
                    lbl.setStyleSheet("color: #ff1744;")

class ConfigScreen(QWidget):
    """Pantalla de Ajustes: gestión de vehículos guardados."""

    vehicle_changed = pyqtSignal()

    def __init__(self, vehicle_manager):
        super().__init__()
        self.vm = vehicle_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # ── Header ───────────────────────────────────────────────────────────
        h_row = QHBoxLayout()
        lbl_title = QLabel("⚙️   VEHÍCULOS CONFIGURADOS")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00e5ff;")
        h_row.addWidget(lbl_title)
        h_row.addStretch()
        btn_add = QPushButton("➕  Agregar Vehículo")
        btn_add.setMinimumHeight(36)
        btn_add.setStyleSheet(
            "background-color:#007acc; color:white; font-weight:bold; padding:0 14px;"
        )
        btn_add.clicked.connect(self.add_vehicle)
        h_row.addWidget(btn_add)
        layout.addLayout(h_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("border:1px solid #2a2a2a;")
        layout.addWidget(sep)

        lbl_hint = QLabel("El vehículo activo aparece en el encabezado y se usa como referencia en escaneos.")
        lbl_hint.setStyleSheet("color:#666; font-size:11px;")
        layout.addWidget(lbl_hint)

        # ── Lista scrollable ──────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.cards_widget = QWidget()
        self.cards_widget.setStyleSheet("background:transparent;")
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.cards_widget)
        layout.addWidget(scroll)

        self.refresh_list()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def refresh_list(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        vehicles = self.vm.get_all()
        active_id = self.vm.data.get("active_vehicle_id")

        if not vehicles:
            lbl = QLabel("No hay vehículos registrados.\n\nUsa '➕ Agregar Vehículo' para comenzar.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color:#555; font-size:14px; padding:40px;")
            self.cards_layout.addWidget(lbl)
            return

        for v in vehicles:
            self.cards_layout.addWidget(self._make_card(v, v["id"] == active_id))

    def _make_card(self, v, is_active):
        frame = QFrame()
        frame.setObjectName("MetricCard")
        if is_active:
            frame.setStyleSheet(
                "QFrame#MetricCard{border:2px solid #007acc; border-radius:10px; background-color:#162032;}"
            )

        row = QHBoxLayout(frame)
        row.setContentsMargins(15, 10, 15, 10)

        icon = QLabel("⭐" if is_active else "🚗")
        icon.setStyleSheet("font-size:22px;")
        row.addWidget(icon)

        col = QVBoxLayout()
        name_lbl = QLabel(f"{v['brand']} {v['model']}")
        color = "#00e5ff" if is_active else "#e0e0e0"
        name_lbl.setStyleSheet(f"font-size:14px; font-weight:bold; color:{color};")
        year_lbl = QLabel(f"Año: {v['year']}")
        year_lbl.setStyleSheet("color:#777; font-size:11px;")
        col.addWidget(name_lbl)
        col.addWidget(year_lbl)
        row.addLayout(col)
        row.addStretch()

        if is_active:
            badge = QLabel("ACTIVO")
            badge.setStyleSheet(
                "background-color:#007acc; color:white; padding:3px 9px;"
                " border-radius:4px; font-size:11px; font-weight:bold;"
            )
            row.addWidget(badge)
        else:
            btn_act = QPushButton("Activar")
            btn_act.setFixedWidth(72)
            btn_act.setMinimumHeight(30)
            btn_act.clicked.connect(lambda _, vid=v["id"]: self.activate_vehicle(vid))
            row.addWidget(btn_act)

        btn_del = QPushButton("🗑")
        btn_del.setFixedWidth(38)
        btn_del.setMinimumHeight(30)
        btn_del.setStyleSheet(
            "background-color:#3a1212; color:#ff5555; border:1px solid #5a2222;"
        )
        btn_del.clicked.connect(lambda _, vid=v["id"]: self.delete_vehicle(vid))
        row.addWidget(btn_del)
        return frame

    # ── Slots ─────────────────────────────────────────────────────────────────

    def add_vehicle(self):
        dlg = VehicleSetupDialog(self, "Agregar Vehículo")
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_data()
            if d["model"]:
                self.vm.add_vehicle(d["brand"], d["model"], d["year"])
                self.refresh_list()
                self.vehicle_changed.emit()

    def activate_vehicle(self, vid):
        self.vm.set_active(vid)
        self.refresh_list()
        self.vehicle_changed.emit()

    def delete_vehicle(self, vid):
        reply = QMessageBox.question(
            self, "Eliminar Vehículo",
            "¿Estás seguro de que deseas eliminar este vehículo?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.vm.remove_vehicle(vid)
            self.refresh_list()
            self.vehicle_changed.emit()


# ─── VENTANA PRINCIPAL ───────────────────────────────────────────────────────

class MasterWindow(QMainWindow):
    def __init__(self, vehicle_manager):
        super().__init__()
        self.vm = vehicle_manager
        self.scan_vehicle_id = None

        self.setWindowTitle("RR-Engineer")
        self.resize(1280, 720)

        # ── Estilos ──────────────────────────────────────────────────────────
        script_dir = os.path.dirname(os.path.abspath(__file__))
        styles_path = os.path.join(script_dir, "styles.qss")
        try:
            with open(styles_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception:
            print(f"No se encontró {styles_path}, aplicando ESTILO_CSS interno.")
            self.setStyleSheet(ESTILO_CSS)

        # ── Layout raíz ──────────────────────────────────────────────────────
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(190)
        self.sidebar.addItem("📈   Dashboard")
        self.sidebar.addItem("🔧   Escáner DTC")
        self.sidebar.addItem("☁️   Emisiones")
        self.sidebar.addItem("⚙️   Ajustes")
        self.sidebar.currentRowChanged.connect(self.cambiar_pagina)
        main_layout.addWidget(self.sidebar)

        # ── Área de contenido ─────────────────────────────────────────────────
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(12, 12, 12, 8)
        content_layout.setSpacing(10)
        main_layout.addLayout(content_layout)

        # Header
        self.header = HeaderApp()
        content_layout.addWidget(self.header, 0)

        # Stack de páginas
        self.stack = QStackedWidget()
        self.dash = Dashboard()
        self.dtc = DTCScreen()
        self.emisiones = EmissionsScreen()
        self.config_screen = ConfigScreen(self.vm)

        self.stack.addWidget(self.dash)          # 0
        self.stack.addWidget(self.dtc)           # 1
        self.stack.addWidget(self.emisiones)     # 2
        self.stack.addWidget(self.config_screen) # 3

        content_layout.addWidget(self.stack, 1)

        # Logger
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(85)
        content_layout.addWidget(self.txt_log, 0)

        # ── Hilo OBD ──────────────────────────────────────────────────────────
        self.obd = HiloOBD()
        self.obd.start()
        self.is_connected = False

        # ── Señales ───────────────────────────────────────────────────────────
        self.header.btn_connect.clicked.connect(self.conectar_obd)
        self.dtc.btn_scan.clicked.connect(self.scan_dtc)
        self.emisiones.btn_check.clicked.connect(self.check_emisiones)
        self.config_screen.vehicle_changed.connect(self.on_vehicle_changed)

        self.obd.conexion.connect(self.update_connection_status)
        self.obd.dato_sensor.connect(self.dash.update_val)
        self.obd.datos_calculados.connect(self.dash.update_calc)
        self.obd.nuevo_dtc.connect(self.on_dtc_result)
        self.obd.nuevo_freeze_frame.connect(self.dtc.mostrar_freeze_frame)
        self.obd.estado_emisiones.connect(self.on_emissions_result)
        self.obd.log.connect(self.txt_log.append)

        # ── Página inicial + vehículo ──────────────────────────────────────────
        self.sidebar.setCurrentRow(0)
        self._update_vehicle_label()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _update_vehicle_label(self):
        v = self.vm.get_active()
        if v:
            self.header.lbl_vehicle.setText(f"🚗  {VehicleManager.display_name(v)}")
            self.header.lbl_vehicle.show()
        else:
            self.header.lbl_vehicle.hide()

    # ── Slots UI ──────────────────────────────────────────────────────────────

    def cambiar_pagina(self, index):
        self.stack.setCurrentIndex(index)
        self.obd.in_dashboard = (index == 0)

    def on_vehicle_changed(self):
        self._update_vehicle_label()

    def conectar_obd(self):
        if not self.is_connected:
            port = self.header.combo_ports.currentText()
            device = port.split(" - ")[0] if " - " in port else port
            baud = int(self.header.combo_baud.currentText())
            self.header.btn_connect.setText("CONECTANDO...")
            self.header.btn_connect.setStyleSheet("background-color:#ff9800; color:black;")
            self.obd.conectar(device, baud)
        else:
            self.obd.desconectar()

    def update_connection_status(self, connected):
        self.is_connected = connected
        if connected:
            self.header.status_led.setStyleSheet(
                "background-color:#00e676; border-radius:9px; border:2px solid #00a854;"
            )
            self.header.lbl_status_text.setText("CONECTADO")
            self.header.btn_connect.setText("DESCONECTAR")
            self.header.btn_connect.setObjectName("DisconnectButton")
            self.header.btn_connect.setStyleSheet("background-color:#d32f2f; color:white;")
        else:
            self.header.status_led.setStyleSheet(
                "background-color:#ff1744; border-radius:9px; border:2px solid #b2102f;"
            )
            self.header.lbl_status_text.setText("DESCONECTADO")
            self.header.btn_connect.setText("CONECTAR")
            self.header.btn_connect.setObjectName("ConnectButton")
            self.header.btn_connect.setStyleSheet("")

    def scan_dtc(self):
        if not self.is_connected:
            QMessageBox.critical(self, "Error", "No hay conexión con el vehículo.")
            return

        vehicles = self.vm.get_all()
        if not vehicles:
            QMessageBox.warning(
                self, "Sin vehículos",
                "No tienes vehículos registrados.\nVe a ⚙️ Ajustes y agrega un vehículo primero."
            )
            return

        dlg = VehicleSelectDialog(vehicles, self)
        if dlg.exec_() != QDialog.Accepted:
            return

        self.scan_vehicle_id = dlg.selected_vehicle_id()
        self.dtc.btn_scan.setEnabled(False)
        self.dtc.btn_scan.setText("ESCANEANDO...")
        self.obd.solicitud_dtc = True

    def check_emisiones(self):
        if not self.is_connected:
            QMessageBox.critical(self, "Error", "No hay conexión con el vehículo.")
            return
        self.emisiones.btn_check.setEnabled(False)
        self.emisiones.btn_check.setText("VERIFICANDO...")
        self.obd.solicitud_emisiones = True

    def on_dtc_result(self, codes, raw):
        vehicle_name = ""
        if self.scan_vehicle_id:
            v = self.vm.get_by_id(self.scan_vehicle_id)
            if v:
                vehicle_name = VehicleManager.display_name(v)
        self.dtc.mostrar_resultados(codes, vehicle_name)
        self.dtc.btn_scan.setEnabled(True)
        self.dtc.btn_scan.setText("INICIAR DIAGNÓSTICO COMPLETO")

    def on_emissions_result(self, data):
        self.emisiones.update_status(data)
        self.emisiones.btn_check.setEnabled(True)
        self.emisiones.btn_check.setText("VERIFICAR MONITORES")


# ─── PUNTO DE ENTRADA ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    vm = VehicleManager(script_dir)

    # ── Diálogo de bienvenida si no hay vehículos ──────────────────────────
    if not vm.has_vehicles():
        dlg = VehicleSetupDialog(title="Bienvenido a RR-Engineer")
        dlg.btn_cancel.hide()          # primer inicio: no se puede cancelar
        dlg.setWindowTitle("RR-Engineer — Configuración Inicial")
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_data()
            if d["model"]:
                vm.add_vehicle(d["brand"], d["model"], d["year"])

    win = MasterWindow(vm)
    win.show()
    sys.exit(app.exec_())