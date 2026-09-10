import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytesseract
from PIL import Image

from telethon import TelegramClient

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)


# ==========================================
# CONFIGURACIÓN
# ==========================================

API_ID = ""
API_HASH = ""
BOT_TOKEN = ""
# ==========================================
# PALABRAS CLAVE
# ==========================================

PALABRAS_CLAVE = [
    "desarrollador",
    "developer",
    "programador",
    "ingeniero de sistemas",
    "ingeniería de sistemas",
    "software",
    "backend",
    "frontend",
    "full stack",
    "fullstack",
    ".net",
    "c#",
    "python",
    "java",
    "javascript",
"ingenieria en sistemas",
"ingeniero en sistemas",
"sistemas",
    "react",
    "angular",
    "sql",
    "devops",

    # QA más específico para evitar falsos positivos
    "qa tester",
    "qa engineer",
    "qa manual",
    "qa automation",
    "quality assurance",

    "tester"
]


# ==========================================
# CLIENTE TELETHON
# ==========================================

telethon_client = TelegramClient(
    "mi_sesion",
    API_ID,
    API_HASH
)


# ==========================================
# BUSCAR COINCIDENCIAS
# ==========================================

def buscar_coincidencias(texto):

    texto = (texto or "").lower()

    coincidencias = []

    for palabra in PALABRAS_CLAVE:

        if palabra in texto:
            coincidencias.append(palabra)

    return coincidencias


# ==========================================
# LEER TEXTO DE IMAGEN
# ==========================================

def leer_imagen(ruta):

    try:

        imagen = Image.open(ruta)

        texto = pytesseract.image_to_string(
            imagen
        )

        return texto

    except Exception as error:

        print(
            f"⚠️ Error leyendo imagen: {error}"
        )

        return ""


# ==========================================
# REVISAR UN MENSAJE
# ==========================================

async def revisar_mensaje(mensaje):

    texto_mensaje = mensaje.message or ""

    coincidencias_texto = buscar_coincidencias(
        texto_mensaje
    )

    coincidencias_imagen = []

    ruta_imagen = None


    # REVISAR FOTO

    if mensaje.photo:

        try:

            print("🖼️ Analizando imagen...")

            ruta_imagen = (
                await mensaje.download_media()
            )

            if ruta_imagen:

                texto_imagen = leer_imagen(
                    ruta_imagen
                )

                coincidencias_imagen = (
                    buscar_coincidencias(
                        texto_imagen
                    )
                )

        except Exception as error:

            print(
                f"⚠️ Error procesando imagen: "
                f"{error}"
            )


    # UNIR SIN DUPLICADOS

    coincidencias = []

    for palabra in (
        coincidencias_texto +
        coincidencias_imagen
    ):

        if palabra not in coincidencias:

            coincidencias.append(palabra)


    if coincidencias:

        return {

            "coincidencias": coincidencias,

            "coincidencias_texto":
                coincidencias_texto,

            "coincidencias_imagen":
                coincidencias_imagen,

            "texto_mensaje":
                texto_mensaje,

            "ruta_imagen":
                ruta_imagen

        }


    # BORRAR IMAGEN SI NO HUBO RESULTADO

    if ruta_imagen:

        try:

            if os.path.exists(ruta_imagen):

                os.remove(ruta_imagen)

        except:
            pass


    return None


# ==========================================
# ENVIAR RESULTADO
# ==========================================

async def enviar_resultado(
    bot,
    chat_id,
    resultado,
    fecha
):

    coincidencias = (
        resultado["coincidencias"]
    )

    coincidencias_texto = (
        resultado["coincidencias_texto"]
    )

    coincidencias_imagen = (
        resultado["coincidencias_imagen"]
    )

    texto_mensaje = (
        resultado["texto_mensaje"]
    )

    ruta_imagen = (
        resultado["ruta_imagen"]
    )


    mensaje_alerta = (

        "🚨 POSIBLE VACANTE\n\n"

        f"📅 Fecha: "
        f"{fecha.strftime('%d/%m/%Y %H:%M')}\n\n"

        f"🔎 Coincidencia: "
        f"{', '.join(coincidencias)}"
    )


    if coincidencias_texto:

        mensaje_alerta += (

            "\n\n📝 Detectado en el texto:\n"

            f"{', '.join(coincidencias_texto)}"
        )


    if coincidencias_imagen:

        mensaje_alerta += (

            "\n\n🖼️ Detectado en la imagen:\n"

            f"{', '.join(coincidencias_imagen)}"
        )


    if texto_mensaje:

        mensaje_alerta += (

            "\n\n📄 MENSAJE ORIGINAL:\n"

            f"{texto_mensaje}"
        )


    # EVITAR EXCEDER EL LÍMITE

    if len(mensaje_alerta) > 4000:

        mensaje_alerta = (
            mensaje_alerta[:4000]
        )


    await bot.send_message(

        chat_id=chat_id,

        text=mensaje_alerta
    )


    # ENVIAR LA IMAGEN ORIGINAL

    if ruta_imagen:

        try:

            with open(
                ruta_imagen,
                "rb"
            ) as imagen:

                await bot.send_photo(

                    chat_id=chat_id,

                    photo=imagen,

                    caption=(
                        "🖼️ IMAGEN ORIGINAL\n\n"
                        "🔎 Coincidencia: "
                        f"{', '.join(coincidencias_imagen)}"
                    )

                )

        except Exception as error:

            print(
                f"⚠️ Error enviando imagen: "
                f"{error}"
            )


        # BORRAR ARCHIVO TEMPORAL

        try:

            if os.path.exists(ruta_imagen):

                os.remove(ruta_imagen)

        except:
            pass


# ==========================================
# BUSCAR VACANTES
# ==========================================

async def buscar_vacantes(
    bot,
    chat_id,
    grupo_id,
    dias
):

    fecha_limite = (
        datetime.now(timezone.utc)
        - timedelta(days=dias)
    )


    encontrados = 0

    revisados = 0


    try:

        async for mensaje in (
            telethon_client.iter_messages(
                grupo_id
            )
        ):

            if mensaje.date < fecha_limite:

                break


            revisados += 1


            resultado = await revisar_mensaje(
                mensaje
            )


            if resultado:

                encontrados += 1


                print(
                    "🚨 VACANTE ENCONTRADA: "
                    f"{', '.join(resultado['coincidencias'])}"
                )


                await enviar_resultado(

                    bot,

                    chat_id,

                    resultado,

                    mensaje.date

                )


        await bot.send_message(

            chat_id=chat_id,

            text=(
                "========================\n"
                "✅ BÚSQUEDA TERMINADA\n"
                "========================\n\n"

                f"📅 Días revisados: {dias}\n"
                f"📨 Mensajes revisados: "
                f"{revisados}\n"
                f"🚨 Resultados encontrados: "
                f"{encontrados}"
            )

        )


    except Exception as error:

        print(
            f"❌ Error: {error}"
        )


        await bot.send_message(

            chat_id=chat_id,

            text=(
                "❌ Ocurrió un error "
                "durante la búsqueda.\n\n"

                f"{error}"
            )

        )


# ==========================================
# /START
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    keyboard = [

        [

            InlineKeyboardButton(
                "🔎 Buscar vacantes",
                callback_data="buscar"
            )

        ],

        [

            InlineKeyboardButton(
                "📋 Ver mis grupos",
                callback_data="grupos"
            )

        ]

    ]


    await update.message.reply_text(

        "🤖 MONITOR DE VACANTES\n\n"
        "Selecciona una opción:",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )

    )


# ==========================================
# MOSTRAR GRUPOS
# ==========================================

async def mostrar_grupos(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    await query.edit_message_text(
        "🔎 Cargando tus grupos..."
    )


    grupos = []


    async for dialog in (
        telethon_client.iter_dialogs()
    ):

        if dialog.is_group:

            grupos.append(
                (
                    dialog.name,
                    dialog.id
                )
            )


    keyboard = []


    for nombre, grupo_id in grupos[:30]:

        nombre = nombre or "Grupo sin nombre"

        keyboard.append(

            [

                InlineKeyboardButton(

                    nombre[:45],

                    callback_data=(
                        f"grupo_{grupo_id}"
                    )

                )

            ]

        )


    if not keyboard:

        await query.edit_message_text(
            "❌ No encontré grupos."
        )

        return


    await query.edit_message_text(

        "📋 SELECCIONA UN GRUPO\n\n"
        "Elige dónde buscar vacantes:",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )

    )


# ==========================================
# SELECCIONAR GRUPO
# ==========================================

async def seleccionar_grupo(
    update,
    context
):

    query = update.callback_query

    await query.answer()


    grupo_id = int(

        query.data.replace(
            "grupo_",
            ""
        )

    )


    context.user_data[
        "grupo_id"
    ] = grupo_id


    context.user_data[
        "esperando_dias"
    ] = True


    await query.edit_message_text(

        "📅 ¿CUÁNTOS DÍAS "
        "DESEAS REVISAR?\n\n"

        "✍️ Escribe un número.\n\n"

        "Ejemplos:\n"
        "1\n"
        "3\n"
        "7\n"
        "15\n"
        "30"

    )


# ==========================================
# RECIBIR DÍAS
# ==========================================

async def recibir_dias(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "esperando_dias"
    ):

        return


    texto = (
        update.message.text or ""
    ).strip()


    try:

        dias = int(texto)

    except ValueError:

        await update.message.reply_text(

            "❌ Escribe solamente "
            "un número.\n\n"
            "Ejemplo: 7"

        )

        return


    if dias <= 0:

        await update.message.reply_text(
            "❌ Debes ingresar al menos 1 día."
        )

        return


    grupo_id = context.user_data.get(
        "grupo_id"
    )


    context.user_data[
        "esperando_dias"
    ] = False


    await update.message.reply_text(

        "🔎 INICIANDO BÚSQUEDA\n\n"

        f"📅 Revisando los últimos "
        f"{dias} día(s)...\n\n"

        "⏳ Puede tardar un momento.\n"
        "📩 Los resultados llegarán "
        "a este chat."

    )


    await buscar_vacantes(

        context.bot,

        update.effective_chat.id,

        grupo_id,

        dias

    )


# ==========================================
# BOTONES
# ==========================================

async def botones(
    update,
    context
):

    query = update.callback_query


    if query.data in (
        "buscar",
        "grupos"
    ):

        await mostrar_grupos(
            update,
            context
        )


    elif query.data.startswith(
        "grupo_"
    ):

        await seleccionar_grupo(
            update,
            context
        )


# ==========================================
# MAIN
# ==========================================

async def main():

    print(
        "🤖 Iniciando Monitor de Vacantes..."
    )


    # CONECTAR TU CUENTA

    await telethon_client.start()

    print(
        "✅ Telethon conectado"
    )


    # CREAR BOT

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )


    # HANDLERS

    app.add_handler(

        CommandHandler(
            "start",
            start
        )

    )


    app.add_handler(

        CallbackQueryHandler(
            botones
        )

    )


    app.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            recibir_dias

        )

    )


    # INICIAR

    await app.initialize()

    await app.start()

    await app.updater.start_polling()


    print(
        "🤖 BOT INICIADO CORRECTAMENTE"
    )


    try:

        await asyncio.Event().wait()


    finally:

        await app.updater.stop()

        await app.stop()

        await app.shutdown()

        await telethon_client.disconnect()


# ==========================================
# EJECUTAR
# ==========================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "\n🛑 Programa detenido."
        )
