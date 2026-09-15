import os               #Para trabajar con rutas del sistema
import requests         #Para hacer peticinoes http al servidor de LLM
import pdfplumber       #Para abrir archivos pdf
import pandas as pd     #Para organizar los datos en una tabla y exportarlos a CSV

#Primero defino el directorio donde estarán los archivos pdf
directorio = "data"

#Luego listo los archivos pdf de "data" que contengan "factura" en el nombre
archivos_factura = [
    os.path.join(directorio, f) 
    for f in os.listdir(directorio) 
    if "factura" in f.lower() and f.endswith(".pdf")
]

#Configuro la conexión con LM Studio
base_url = "http://localhost:1234/v1"
api_key = "lm-studio"
myModel = "qwen2.5-3b-instruct"

#Lista para almecenar resultados
datos_extraidos = []

#Prompt que se enviará al modelo
system_prompt = (
    "You are going to receive invoice data in text format. Read it and identify the following three fields:\n"
    "1. Customer Name\n"
    "2. Date\n"
    "3. Total Amount\n\n"
    "Return the three fields separated ONLY by a vertical bar (|) on a single line in this exact format:\n"
    "Customer | Date | Total Amount\n\n"
    "Do not include headers, quotes, extra line breaks, or explanations."
)

#Cabeceras http para autenticarse
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

#Creo un bucle para procesar cada pdf
for pdf_file in archivos_factura:
    print(f"Procesando: {pdf_file}...")
    
    #Extraigo el texto
    pdf_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            pdf_text += page.extract_text() or ""
            
    #Estructura de la petición http
    body = {
        "model": myModel,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pdf_text}
        ],
        "temperature": 0.1  #Asigno una temperatura baja para mayor precisión
    }
    
    #Envio el "body" cono json a LM Studio y convierto la respuesta en un diccionario Pyhton
    try:
        response = requests.post(f"{base_url}/chat/completions", json=body, headers=headers)
        parsed_content = response.json()
        
        #Si contiene el apartado "choices" es que ha tenido exito, y se extrae la info quitando los espacios sobrantes
        if 'choices' in parsed_content:
            message_content = parsed_content['choices'][0]['message']['content'].strip()
            
            #Separo el texto utilizando el delimitador |
            partes = [p.strip() for p in message_content.split('|')]
            
            #Asigno a cada parte su variable
            cliente = partes[0] if len(partes) > 0 else ""
            fecha = partes[1] if len(partes) > 1 else ""
            monto = partes[2] if len(partes) > 2 else ""
            
            #Guardo los 3 valores como un diccionario
            datos_extraidos.append({
                'Customer': cliente,
                'Date': fecha,
                'Total_Amount': monto
            })
        
        #Si la respuesta no tiene "choices" añado una fila con "ERROR API"
        else:
            print(f"Error devuelto por la API en {pdf_file}: {parsed_content.get('error')}")
            datos_extraidos.append({'Customer': 'ERROR API', 'Date': 'ERROR API', 'Total_Amount': 'ERROR API'})
            
    #Capturo las excepciones y las muestro por consola y en la tabla
    except Exception as e:
        print(f"Error de conexión procesando {pdf_file}: {e}")
        datos_extraidos.append({'Customer': 'ERROR CONEXION', 'Date': 'ERROR CONEXION', 'Total_Amount': 'ERROR CONEXION'})

#Creao el DataFrame e importo a excel
df = pd.DataFrame(datos_extraidos)

#Guardo en CSV separado por punto y coma para que no se descuadre 
archivo_salida = "resultados_facturas.csv"
df.to_csv(archivo_salida, index=False, sep=";", encoding="utf-8-sig")

print(f"\nProceso finalizado. Archivo guardado correctamente en: {archivo_salida}")