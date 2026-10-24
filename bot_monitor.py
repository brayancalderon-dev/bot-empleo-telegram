import asyncio
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from html.parser import HTMLParser

import pytesseract
from PIL import Image, ImageOps
from telethon import TelegramClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
API_ID = ""
API_HASH = ""
BOT_TOKEN = ""

# Ajustes de rendimiento
TIMEOUT_BUSQUEDA_WEB = 4          # Segundos máximos por búsqueda web
MAX_ANCHO_OCR = 1500              # Reduce memoria/CPU al leer afiches
MAX_TEXTO_ALERTA = 3900           # Telegram admite hasta 4096 caracteres
MAX_GRUPOS_EN_MENU = 50

# Cargos y áreas tecnológicas (incluye títulos alternativos, no solo "Sistemas")
CARGOS_IT = [
    "desarrollador", "desarrolladora", "developer", "software engineer",
    "ingeniero de software", "ingeniera de software", "programador", "programadora",
    "programador de sistemas", "programador web", "desarrollador web",
    "backend", "back end", "frontend", "front end", "full stack", "fullstack",
    "analista de sistemas", "analista sistemas", "ingeniero de sistemas",
    "ingeniera de sistemas", "administrador de sistemas", "administradora de sistemas",
    "administrador de base de datos", "administrador de bases de datos", "administrador de bd", "dba",
    "analista de datos", "data analyst", "data engineer", "ingeniero de datos",
    "cientifico de datos", "data scientist", "business intelligence", "bi developer",
    "power bi developer", "desarrollador bi", "especialista power bi",
    "qa engineer", "qa tester", "qa automation", "tester de software", "analista qa",
    "quality assurance", "automation tester", "devops", "site reliability", "sre",
    "cloud engineer", "ingeniero cloud", "arquitecto de software", "software architect",
    "soporte ti", "soporte tecnico informatico", "soporte tecnico", "tecnico de soporte",
    "analista de soporte", "tecnico informatico", "tecnico de sistemas", "tecnico en sistemas",
    "help desk", "helpdesk", "service desk", "mesa de ayuda", "soporte de aplicaciones",
    "administrador de redes", "administradora de redes", "ingeniero de redes", "network engineer",
    "analista de redes", "ciberseguridad", "analista de seguridad informatica", "security analyst",
    "seguridad informatica", "auditor informatico", "auditoria informatica",
    "especialista en seguridad de la informacion", "consultor sap", "desarrollador sap",
    "consultor tecnologico", "especialista de aplicaciones", "analista de aplicaciones",
    "etl developer", "desarrollador etl", "integrador de sistemas", "scrum master tecnico",
    "ingeniero informatico", "ingeniera informatica", "ingeniero en computacion",
    "ingeniera en computacion", "analista informatico", "especialista en sistemas",
    "especialista de sistemas", "analista de infraestructura", "especialista en infraestructura",
    "administrador de aplicaciones", "administrador de servidores", "administradora de servidores",
    "administrador de base de datos", "administrador de bases de datos", "tecnico de infraestructura",
    "especialista de tecnologia", "especialista en tecnologia", "coordinador de tecnologia",
    "jefe de sistemas", "jefe de tecnologia", "gerente de tecnologia", "it support",
    "it support specialist", "it analyst", "systems administrator", "system administrator",
]

TECNOLOGIAS = [
    ".net", "c#", "c++", "python", "java", "javascript", "typescript", "angular", "react", "vue",
    "node.js", "nodejs", "php", "laravel", "spring boot", "django", "flask", "sql server", "sql",
    "mysql", "postgresql", "oracle", "mongodb", "power bi", "power query", "dax", "excel avanzado",
    "etl", "ssis", "dtsx", "azure", "aws", "gcp", "docker", "kubernetes", "linux", "git",
    "api rest", "apis rest", "microservicios", "selenium", "cypress", "playwright", "redes", "firewall",
    "sap", "salesforce", "sharepoint", "power automate", "machine learning", "inteligencia artificial",
    "data warehouse", "active directory", "windows server", "vmware", "hyper-v", "tcp/ip", "itil",
]

# Exclusiones para reducir avisos de puestos que no son tecnológicos.
CARGOS_NO_IT = [
    "asesor comercial", "asesora comercial", "ejecutivo comercial", "ejecutiva comercial",
    "asesor de ventas", "asesora de ventas", "vendedor", "vendedora", "promotor de ventas",
    "call center ventas", "teleoperador comercial", "cajero", "cajera", "mesero", "mesera",
    "cocinero", "cocinera", "auxiliar de limpieza", "personal de limpieza", "guardia de seguridad",
    "conductor", "chofer", "repartidor", "impulsadora", "mercaderista", "operario de produccion",
    "bodeguero", "auxiliar de bodega", "estibador", "asistente contable", "contador", "contadora",
    "recepcionista", "secretaria", "asesor financiero comercial", "asesor de cobranza",
]

UBICACIONES_PERMITIDAS = [
    # Quito y alrededores
    "quito", "cumbaya", "tumbaco", "sangolqui", "ruminahui", "valle de los chillos",
    "conocoto", "pomasqui", "calderon", "mejia", "machachi", "distrito metropolitano de quito",
    # Latacunga y alrededores
    "latacunga", "salcedo", "saquisili", "pujili", "sigchos", "pangua", "la mana", "cotopaxi",
    # Ambato y alrededores
    "ambato", "pelileo", "banos", "cevallos", "quero", "mocha", "tisaleo", "patate", "tungurahua",
]

UBICACIONES_NO_PERMITIDAS_CONOCIDAS = [
    "guayaquil", "cuenca", "manta", "portoviejo", "santo domingo", "riobamba", "ibarra", "loja",
    "esmeraldas", "machala", "quevedo", "babahoyo", "milagro", "duran", "salinas", "azogues",
    "tulcan", "nueva loja", "lago agrio", "macas", "zamora", "puerto ayora",
]

REMOTO = [
    "trabajo remoto", "100% remoto", "100 % remoto", "modalidad remota", "remoto", "remota",
    "teletrabajo", "desde casa", "home office", "work from home", "full remote", "remote work", "wfh",
]

CIUDADES_ECUADOR = [
    "Quito", "Latacunga", "Ambato", "Guayaquil", "Cuenca", "Manta", "Portoviejo",
    "Santo Domingo", "Riobamba", "Ibarra", "Loja", "Esmeraldas", "Machala", "Quevedo",
    "Duran", "Salinas", "Babahoyo", "Milagro", "Sangolqui", "Cumbaya", "Tumbaco",
    "Salcedo", "Pujili", "Saquisili", "Pelileo", "Banos", "Cevallos", "Cotopaxi", "Tungurahua",
    "Pichincha", "Guayas", "Azuay", "Manabi", "El Oro", "Chimborazo", "Imbabura",
]

telethon_client = None


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip()


def contiene_frase(texto_normalizado: str, frases: list[str]) -> list[str]:
    """Busca variantes sin volver a normalizar el texto completo por cada frase."""
    resultado = []
    for frase in frases:
        frase_n = normalizar(frase)
        if not frase_n:
            continue
        if len(frase_n) <= 4 and frase_n.replace(".", "").isalnum():
            patron = r"(?<![a-z0-9])" + re.escape(frase_n) + r"(?![a-z0-9])"
            coincide = re.search(patron, texto_normalizado) is not None
        else:
            coincide = frase_n in texto_normalizado
        if coincide:
            resultado.append(frase)
    return resultado


def es_modalidad_remota(texto: str, texto_normalizado: str) -> bool:
    """Detecta teletrabajo real, no frases técnicas como 'acceso remoto a equipos'."""
    frases_explicitas = (
        "trabajo remoto", "vacante remota", "vacante remoto", "modalidad remota",
        "modalidad remoto", "100% remoto", "100 % remoto", "100% remota",
        "100 % remota", "teletrabajo", "home office", "work from home",
        "full remote", "remote work", "wfh", "desde casa",
        "posicion remota", "puesto remoto", "puesto remoto", "trabajar remotamente",
    )
    if any(normalizar(frase) in texto_normalizado for frase in frases_explicitas):
        return True

    # Acepta 'Remoto' solo cuando aparece como valor de ubicación/modalidad o en una línea independiente.
    for linea in (texto or "").splitlines():
        linea_n = normalizar(linea).strip(" .:;-•|")
        if re.fullmatch(r"(?:ubicacion|localidad|modalidad|tipo de trabajo|lugar de trabajo)\s*:?\s*(?:100\s*%?\s*)?remot[oa]", linea_n):
            return True
        if re.fullmatch(r"(?:100\s*%?\s*)?remot[oa]", linea_n):
            return True
    return False


def limpiar_texto_ocr(texto: str, max_caracteres: int = 2400) -> str:
    """Reduce basura típica del OCR de afiches sin alterar el archivo de imagen original."""
    lineas_limpias = []
    vistas = set()
    for linea in (texto or "").splitlines():
        linea = re.sub(r"[ \t]+", " ", linea).strip(" \t|_")
        if len(linea) < 3:
            continue
        letras = sum(ch.isalpha() for ch in linea)
        alfanumericos = sum(ch.isalnum() for ch in linea)
        if letras < 3 or alfanumericos == 0 or letras / max(1, len(re.sub(r"\s", "", linea))) < 0.38:
            continue
        clave = normalizar(linea)
        if clave and clave not in vistas:
            vistas.add(clave)
            lineas_limpias.append(linea)
    return "\n".join(lineas_limpias)[:max_caracteres].strip()


def detectar_ciudades(texto_normalizado: str) -> list[str]:
    """Detecta ciudades con límites de palabra para reducir falsos positivos."""
    encontradas = []
    for ciudad in CIUDADES_ECUADOR:
        cn = normalizar(ciudad)
        if cn and re.search(r"(?<![a-z])" + re.escape(cn) + r"(?![a-z])", texto_normalizado):
            if ciudad not in encontradas:
                encontradas.append(ciudad)
    return encontradas


def detectar_ciudad_en_campo(texto_normalizado: str) -> str | None:
    """Prioriza la ciudad escrita junto a LOCALIDAD/UBICACIÓN/LUGAR DE TRABAJO."""
    etiquetas = r"(?:localidad|ubicacion|lugar de trabajo|ciudad|ubicacion del puesto|sede)"
    m = re.search(etiquetas + r"\s*[:=\-]?\s*(.{0,100})", texto_normalizado)
    if not m:
        return None
    ciudades = detectar_ciudades(m.group(1))
    return ciudades[0] if ciudades else None


# Frases que suelen identificar campañas de cursos/certificaciones, no ofertas laborales.
ANUNCIO_CAPACITACION = [
    "base de certificaciones", "base de certificacion", "certificaciones oficiales",
    "certificaciones microsoft", "certificacion microsoft", "regístrate aquí", "registrate aqui",
    "esta invitacion es para ti", "fortaleciendo nuestra comunidad",
    "comunidad de talento tecnologico", "az-140", "az-700",
]
INDICADORES_VACANTE_REAL = [
    "vacante", "oferta laboral", "oferta de empleo", "estamos contratando",
    "se busca", "se requiere", "se necesita", "envia tu hoja de vida",
    "envia tu cv", "enviar hoja de vida", "postula aqui", "postular a la vacante",
    "aplica a esta vacante", "contrato indefinido", "salario", "sueldo",
    "jornada laboral", "experiencia previa", "experiencia minima",
]

def es_invitacion_capacitacion(texto_normalizado: str) -> bool:
    """Descarta anuncios para crear bases de certificaciones, cursos o registros."""
    tiene_senal_capacitacion = any(normalizar(x) in texto_normalizado for x in ANUNCIO_CAPACITACION)
    if not tiene_senal_capacitacion:
        return False
    tiene_vacante_real = any(normalizar(x) in texto_normalizado for x in INDICADORES_VACANTE_REAL)
    # Los códigos de certificación más una invitación a registrarse no son una vacante.
    tiene_codigo_cert = bool(re.search(r"\baz[- ]?\d{3}\b", texto_normalizado))
    invitacion_registro = any(normalizar(x) in texto_normalizado for x in ("registrate aqui", "esta invitacion es para ti"))
    if tiene_codigo_cert and invitacion_registro and not tiene_vacante_real:
        return True
    if ("base de certificaciones" in texto_normalizado or "comunidad de talento tecnologico" in texto_normalizado) and not tiene_vacante_real:
        return True
    return False


def evaluar_vacante(texto: str) -> dict | None:
    texto = (texto or "").strip()
    if len(texto) < 8:
        return None

    tn = normalizar(texto)
    # Evita alertas de invitaciones a certificaciones/capacitaciones que mencionan Azure,
    # redes o tecnología pero no ofrecen un puesto de trabajo.
    if es_invitacion_capacitacion(tn):
        return None

    cargos = contiene_frase(tn, CARGOS_IT)
    if not cargos:
        return None

    tecnologias = contiene_frase(tn, TECNOLOGIAS)
    ciudades = detectar_ciudades(tn)
    ciudad_campo = detectar_ciudad_en_campo(tn)
    ubicaciones = contiene_frase(tn, UBICACIONES_PERMITIDAS)
    remoto = contiene_frase(tn, REMOTO)
    permitidas_norm = {normalizar(x) for x in UBICACIONES_PERMITIDAS}
    ciudad_campo_norm = normalizar(ciudad_campo) if ciudad_campo else ""
    otras_ciudades = [c for c in ciudades if normalizar(c) not in permitidas_norm]

    # Si la ciudad aparece en el campo de ubicación, manda ese dato por encima
    # de palabras como "remoto" que el OCR pudiera haber interpretado mal.
    if ciudad_campo and ciudad_campo_norm not in permitidas_norm:
        return None
    if otras_ciudades and not ubicaciones and not remoto:
        return None

    cargos_generales = (
        "soporte tecnico", "tecnico de soporte", "analista de soporte", "tecnico informatico",
        "tecnico de sistemas", "help desk", "helpdesk", "service desk", "mesa de ayuda",
        "administrador de sistemas", "administrador de redes", "ingeniero de redes",
        "ciberseguridad", "seguridad informatica", "auditor informatico", "auditoria informatica",
        "analista de infraestructura", "administrador de servidores", "ingeniero informatico",
        "ingeniero en computacion", "ingeniero de software", "desarrollador", "programador",
        "qa engineer", "qa tester", "dba", "data analyst", "data engineer", "devops",
        "tecnico sr", "tecnico senior", "networking", "telecomunicaciones",
    )
    cargo_general = any(normalizar(c) in tn for c in cargos_generales)
    if not tecnologias and not cargo_general:
        return None

    ubicacion_detectada = ciudad_campo or (ubicaciones[0] if ubicaciones else (ciudades[0] if ciudades else ""))
    remoto_real = bool(remoto) and not (ciudad_campo and ciudad_campo_norm not in permitidas_norm)
    return {
        "cargos": cargos[:8],
        "tecnologias": tecnologias[:10],
        "ubicaciones": ubicaciones[:6],
        "ciudades_detectadas": ciudades[:6],
        "ubicacion_detectada": ubicacion_detectada,
        "ciudad_en_campo": ciudad_campo or "",
        "remoto": remoto_real,
        "ubicacion_faltante": not ubicacion_detectada and not remoto_real,
    }


class TextoHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.partes = []

    def handle_data(self, data):
        if data and data.strip():
            self.partes.append(data.strip())


@lru_cache(maxsize=96)
def buscar_ubicacion_web_sync(texto: str) -> str:
    """Consulta una búsqueda pública; devuelve pistas, no una dirección garantizada."""
    limpio = re.sub(r"\s+", " ", texto or "").strip()
    if len(limpio) < 20:
        return "No hay suficiente texto para investigar la ubicación."

    # Las primeras líneas suelen contener empresa y cargo. Evita enviar el anuncio completo.
    consulta = (limpio[:230] + " empresa dirección ubicación Ecuador").strip()
    url_busqueda = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(consulta)
    try:
        req = urllib.request.Request(
            url_busqueda,
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124 Safari/537.36"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_BUSQUEDA_WEB) as resp:
            pagina = resp.read(350_000).decode("utf-8", errors="ignore")
        parser = TextoHTML()
        parser.feed(pagina)
        texto_web = normalizar(" ".join(parser.partes))
        ciudades = []
        for ciudad in CIUDADES_ECUADOR:
            ciudad_n = normalizar(ciudad)
            if ciudad_n and re.search(r"(?<![a-z])" + re.escape(ciudad_n) + r"(?![a-z])", texto_web):
                # Evita nombres repetidos por variantes de tilde.
                if ciudad not in ciudades:
                    ciudades.append(ciudad)
        if ciudades:
            return (
                "La búsqueda web menciona: " + ", ".join(ciudades[:4]) + ". "
                "Es una pista, no una confirmación de la sede del puesto. Revisa: " + url_busqueda
            )
        return "No encontré una ciudad clara en la búsqueda web. Ubicación por confirmar: " + url_busqueda
    except Exception as exc:
        return f"No se pudo consultar la web ({type(exc).__name__}). Verifica manualmente: {url_busqueda}"


async def buscar_ubicacion_web(texto: str) -> str:
    # La consulta se ejecuta en un hilo para no bloquear el bot.
    clave = re.sub(r"\s+", " ", texto or "").strip()[:400]
    return await asyncio.to_thread(buscar_ubicacion_web_sync, clave)


def leer_imagen(ruta: str) -> str:
    """OCR con imagen reducida a escala de grises para consumir menos memoria."""
    try:
        with Image.open(ruta) as original:
            img = ImageOps.exif_transpose(original).convert("L")
            if img.width > MAX_ANCHO_OCR:
                alto = max(1, int(img.height * (MAX_ANCHO_OCR / img.width)))
                img = img.resize((MAX_ANCHO_OCR, alto))
            try:
                return pytesseract.image_to_string(img, lang="spa+eng", config="--psm 6")
            except Exception:
                return pytesseract.image_to_string(img, lang="eng", config="--psm 6")
    except Exception as exc:
        print(f"⚠️ OCR no disponible para una imagen: {type(exc).__name__}")
        return ""


def es_imagen(mensaje) -> bool:
    if getattr(mensaje, "photo", None):
        return True
    documento = getattr(mensaje, "document", None)
    mime = getattr(documento, "mime_type", "") if documento else ""
    return bool(mime and mime.startswith("image/"))


async def revisar_mensaje(mensaje):
    texto_mensaje = (mensaje.message or "").strip()
    texto_imagen = ""
    ruta_imagen = None
    evaluacion = evaluar_vacante(texto_mensaje) if texto_mensaje else None
    imagen = es_imagen(mensaje)

    # Solo ejecuta OCR en imágenes que pueden ser relevantes o cuando la
    # ubicación del texto/caption está ausente o parece remota y necesita validar.
    necesita_ocr = imagen and (
        not evaluacion
        or evaluacion.get("ubicacion_faltante", False)
        or bool(evaluacion.get("remoto", False))
    )
    if necesita_ocr:
        try:
            ruta_imagen = await mensaje.download_media()
            if ruta_imagen:
                texto_imagen = await asyncio.to_thread(leer_imagen, ruta_imagen)
                combinado = "\n".join(x for x in (texto_mensaje, texto_imagen) if x)
                evaluacion = evaluar_vacante(combinado)
        except Exception as exc:
            print(f"⚠️ No se pudo procesar una imagen: {type(exc).__name__}")

    if not evaluacion:
        if ruta_imagen and os.path.isfile(ruta_imagen):
            try:
                os.remove(ruta_imagen)
            except OSError:
                pass
        return None

    return {
        "evaluacion": evaluacion,
        "texto_mensaje": texto_mensaje,
        "texto_imagen": texto_imagen,
        "ruta_imagen": ruta_imagen,
    }


async def enviar_resultado(bot, chat_id, resultado, fecha, grupo_nombre=""):
    ev = resultado["evaluacion"]
    texto_mensaje = resultado["texto_mensaje"]
    texto_imagen = resultado["texto_imagen"]
    ruta_imagen = resultado["ruta_imagen"]
    ubicacion = ev.get("ubicacion_detectada", "") or ", ".join(ev.get("ubicaciones", []))
    busqueda_web = ""

    if not ubicacion and ev["remoto"]:
        ubicacion = "Remoto (indicado en el anuncio)"
    elif not ubicacion and ev["ubicacion_faltante"]:
        ubicacion = "No indicada en el anuncio"
        busqueda_web = await buscar_ubicacion_web(texto_mensaje + "\n" + texto_imagen)

    partes = [
        "💻 VACANTE IT FILTRADA",
        f"📅 Publicación: {fecha.strftime('%d/%m/%Y %H:%M')} UTC" if fecha else "📅 Fecha de publicación no disponible",
        f"📍 Ubicación detectada: {ubicacion or 'No indicada'}",
        f"👨‍💻 Cargo o área: {', '.join(ev['cargos'])}",
    ]
    if ev["tecnologias"]:
        partes.append(f"🧰 Tecnologías: {', '.join(ev['tecnologias'])}")
    if busqueda_web:
        partes.append(f"🌐 Investigación de ubicación: {busqueda_web}")
    if grupo_nombre:
        partes.append(f"📣 Fuente: {grupo_nombre}")
    # Si el mensaje solo contiene una imagen, no presentamos OCR defectuoso como si fuera
    # el anuncio original: mostramos el texto extraído claramente identificado y enviamos la imagen.
    texto_caption_util = texto_mensaje if len(re.sub(r"[^\w]", "", texto_mensaje, flags=re.UNICODE)) >= 8 else ""
    if texto_caption_util:
        partes.append("\n📝 TEXTO DEL ANUNCIO:\n" + texto_caption_util[:2400])
    elif texto_imagen:
        ocr_limpio = limpiar_texto_ocr(texto_imagen)
        if ocr_limpio:
            partes.append("\n📝 TEXTO DETECTADO EN LA IMAGEN (OCR; puede contener errores):\n" + ocr_limpio)
        else:
            partes.append("\n📝 No se pudo extraer texto legible del afiche. Revisa la imagen original adjunta.")

    alerta = "\n".join(partes)
    if len(alerta) > MAX_TEXTO_ALERTA:
        alerta = alerta[:MAX_TEXTO_ALERTA] + "\n… (texto recortado)"

    try:
        await bot.send_message(chat_id=chat_id, text=alerta, disable_web_page_preview=True)
        if ruta_imagen and os.path.isfile(ruta_imagen):
            with open(ruta_imagen, "rb") as archivo:
                await bot.send_photo(chat_id=chat_id, photo=archivo, caption="🖼️ Imagen original del anuncio")
    finally:
        if ruta_imagen and os.path.isfile(ruta_imagen):
            try:
                os.remove(ruta_imagen)
            except OSError:
                pass


async def actualizar_progreso(bot, chat_id, message_id, texto):
    """Actualiza un único mensaje para informar que el escaneo sigue activo."""
    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=texto, disable_web_page_preview=True
        )
    except Exception as exc:
        # Un fallo al editar el indicador no debe detener la búsqueda.
        print(f"⚠️ No se pudo actualizar el progreso: {type(exc).__name__}")


async def buscar_vacantes(bot, chat_id, grupo_id, dias, grupo_nombre=""):
    fecha_limite = datetime.now(timezone.utc) - timedelta(days=dias)
    encontrados = revisados = descartados = 0
    inicio = datetime.now(timezone.utc)
    mensaje_estado = await bot.send_message(
        chat_id,
        f"🔎 BUSCANDO VACANTES IT\n\n"
        f"📅 Periodo: últimos {dias} día(s)\n"
        "⏳ Estoy revisando mensajes e imágenes. Este aviso se actualizará mientras sigo buscando…"
    )
    ultimo_aviso = inicio
    try:
        async for mensaje in telethon_client.iter_messages(grupo_id):
            if mensaje.date and mensaje.date < fecha_limite:
                break  # Los mensajes llegan del más reciente al más antiguo.
            revisados += 1
            resultado = await revisar_mensaje(mensaje)
            if resultado:
                encontrados += 1
                cargos = ", ".join(resultado["evaluacion"]["cargos"])
                print(f"✅ Vacante: {cargos}")
                await enviar_resultado(bot, chat_id, resultado, mensaje.date, grupo_nombre)

            ahora = datetime.now(timezone.utc)
            # Actualiza el mismo mensaje cada 8 mensajes o cada 12 segundos.
            if revisados % 8 == 0 or (ahora - ultimo_aviso).total_seconds() >= 12:
                await actualizar_progreso(
                    bot, chat_id, mensaje_estado.message_id,
                    "🔎 BUSCANDO VACANTES IT…\n\n"
                    f"📨 Mensajes revisados: {revisados}\n"
                    f"💻 Vacantes encontradas: {encontrados}\n"
                    f"🚫 Anuncios descartados: {revisados - encontrados}\n\n"
                    "⏳ Sigo buscando en los mensajes restantes. Si encuentro otra vacante, te la enviaré y continuaré."
                )
                ultimo_aviso = ahora

        duracion = int((datetime.now(timezone.utc) - inicio).total_seconds())
        await actualizar_progreso(
            bot, chat_id, mensaje_estado.message_id,
            "✅ BÚSQUEDA TERMINADA\n\n"
            f"📅 Periodo: {dias} día(s)\n"
            f"📨 Mensajes revisados: {revisados}\n"
            f"🚫 Anuncios descartados: {revisados - encontrados}\n"
            f"💻 Vacantes enviadas: {encontrados}\n"
            f"⏱️ Tiempo: {duracion} segundos\n\n"
            "Se filtraron ofertas IT para Quito, Latacunga, Ambato y alrededores, o puestos realmente remotos. "
            "Las invitaciones a cursos o bases de certificaciones se descartan."
        )
    except Exception as exc:
        print(f"❌ Error de búsqueda: {type(exc).__name__}: {exc}")
        await actualizar_progreso(
            bot, chat_id, mensaje_estado.message_id,
            "⚠️ LA BÚSQUEDA SE INTERRUMPIÓ\n\n"
            f"📨 Mensajes revisados: {revisados}\n"
            f"💻 Vacantes enviadas: {encontrados}\n"
            f"Error: {type(exc).__name__}: {str(exc)[:500]}"
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("🔎 Buscar vacantes", callback_data="buscar")],
        [InlineKeyboardButton("📋 Ver mis grupos", callback_data="grupos")],
    ]
    await update.message.reply_text(
        "🤖 MONITOR DE VACANTES IT\n\n"
        "Busca puestos de desarrollo, soporte técnico, infraestructura, datos, redes, QA y otras áreas IT.\n"
        "Prioriza Quito, Latacunga, Ambato y alrededores, además de puestos remotos. "
        "Si el anuncio no dice dónde es, lo envía y busca pistas en internet. También descarta invitaciones a cursos o bases de certificaciones.\n\nElige una opción:",
        reply_markup=InlineKeyboardMarkup(teclado),
    )


async def mostrar_grupos(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔎 Cargando grupos de Telegram…")
    grupos = []
    try:
        async for dialog in telethon_client.iter_dialogs():
            if dialog.is_group:
                grupos.append((dialog.name or "Grupo sin nombre", dialog.id))
                if len(grupos) >= MAX_GRUPOS_EN_MENU:
                    break
    except Exception as exc:
        await query.edit_message_text(f"❌ No pude cargar los grupos: {type(exc).__name__}")
        return

    if not grupos:
        await query.edit_message_text("❌ No encontré grupos. Comprueba que tu cuenta pertenezca a ellos.")
        return

    context.user_data["nombres_grupos"] = {str(gid): nombre for nombre, gid in grupos}
    teclado = [[InlineKeyboardButton(nombre[:48], callback_data=f"grupo:{gid}")] for nombre, gid in grupos]
    await query.edit_message_text(
        "📋 SELECCIONA UN GRUPO\n\nElige dónde buscar vacantes:",
        reply_markup=InlineKeyboardMarkup(teclado),
    )


async def seleccionar_grupo(update, context):
    query = update.callback_query
    await query.answer()
    grupo_id = int(query.data.split(":", 1)[1])
    nombres = context.user_data.get("nombres_grupos", {})
    nombre = nombres.get(str(grupo_id), "Grupo seleccionado")
    context.user_data["grupo_id"] = grupo_id
    context.user_data["grupo_nombre"] = nombre
    context.user_data["esperando_dias"] = True
    await query.edit_message_text(
        f"📣 Grupo: {nombre}\n\n📅 ¿Cuántos días deseas revisar?\nEscribe un número entre 1 y 365."
    )


async def recibir_dias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("esperando_dias"):
        return
    try:
        dias = int((update.message.text or "").strip())
    except (ValueError, AttributeError):
        await update.message.reply_text("❌ Escribe solo un número, por ejemplo: 7")
        return
    if not 1 <= dias <= 365:
        await update.message.reply_text("❌ Ingresa una cantidad entre 1 y 365 días.")
        return

    grupo_id = context.user_data.get("grupo_id")
    grupo_nombre = context.user_data.get("grupo_nombre", "")
    if not grupo_id:
        context.user_data["esperando_dias"] = False
        await update.message.reply_text("❌ Selecciona un grupo primero con /start.")
        return
    context.user_data["esperando_dias"] = False
    await update.message.reply_text(
        f"🔎 Buscaré vacantes de los últimos {dias} día(s).\n"
        "Los anuncios sin ubicación se revisan con OCR y una búsqueda web orientativa. Te mostraré el progreso mientras sigo buscando."
    )
    await buscar_vacantes(context.bot, update.effective_chat.id, grupo_id, dias, grupo_nombre)


async def botones(update, context):
    query = update.callback_query
    if query.data in ("buscar", "grupos"):
        await mostrar_grupos(update, context)
    elif query.data.startswith("grupo:"):
        await seleccionar_grupo(update, context)


async def main():
    if not API_ID.strip() or not API_HASH.strip() or not BOT_TOKEN.strip():
        raise RuntimeError("Completa API_ID, API_HASH y BOT_TOKEN al principio de bot_monitor.py")

    global telethon_client
    telethon_client = TelegramClient("mi_sesion", int(API_ID), API_HASH)
    print("🤖 Iniciando Monitor de Vacantes IT…")
    await telethon_client.start()
    print("✅ Cuenta de Telegram conectada")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(botones))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_dias))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ BOT INICIADO. Abre tu bot en Telegram y envía /start")
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await telethon_client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido.")
    except Exception as exc:
        print(f"\n❌ No se pudo iniciar el bot: {type(exc).__name__}: {exc}")
        print("Comprueba la conexión a internet y que el BOT_TOKEN siga vigente.")
        print("Si el error contiene ConnectError, ReadError o Timed out, suele ser un problema de conexión con Telegram.")
