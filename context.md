# 🧠 Prompt — Página Web del Buscador Multiplataforma

Crea una **página web moderna, funcional y visualmente atractiva** para una aplicación llamada **“Buscador Multiplataforma”**, un sistema inteligente que utiliza un **modelo LLM con procesamiento del lenguaje natural (NLP)** para interpretar búsquedas de usuarios y recomendar productos tecnológicos en base a su intención y contexto.

---

## 🎯 Objetivo del proyecto

El propósito de la aplicación es permitir que el usuario escriba lo que necesita en lenguaje natural —por ejemplo:

- “Quiero una computadora para jugar videojuegos.”
- “Busco un mouse ASUS inalámbrico.”
- “¿Qué teclado compacto con luces RGB me recomendás para programar?”
- “Mostrame notebooks HP con buena batería y gráfica dedicada.”

El sistema analiza la búsqueda, **detecta la intención**, y selecciona los **cinco productos más relevantes** desde una **base de datos CSV**, ordenados **descendentemente por su puntaje de scoring**.

---

## ⚙️ Pipeline funcional de la aplicación

1. **Entrada del usuario**  
   El usuario escribe una búsqueda en lenguaje natural en la barra central de la página.

2. **Generación de intención**  
   El modelo LLM procesa el texto, **detecta la intención**, y genera un **archivo JSON** con los datos interpretados.  

   **Ejemplos de salida:**
    - busco una notebook asus.
    {"categoria": "notebook", "intencion": "programacion", "marca": "asus", "atributos": ["2_en_1", "economico"]}

    - busco un mouse asus.
    {"categoria": "mouse", "intencion": "diseño", "marca": "asus", "atributos": ["economico", "inalambrico"]}

    - lo quiero para programacion, ¿qué teclado que sea compacto, sin cables y con lucecitas de colores tenés?
    {"categoria": "teclado", "intencion": "programacion", "atributos": ["compacto_60", "inalambrico", "rgb"]}

3. **Búsqueda en la base de datos**  
Con el JSON generado, el sistema **busca en la base de datos los productos más similares a la petición del usuario**, comparando los campos de categoría, marca y atributos.

4. **Sistema de scoring**  
Cada producto obtiene un **puntaje de similitud (scoring)**. Los cinco con mayor puntuación se seleccionan como resultados finales.

5. **Visualización de resultados**  
Los productos se muestran **ordenados descendentemente según su scoring**, mostrando primero los más relevantes.

---

## 🖥️ Estructura y diseño de la interfaz

- **Banner principal**  
Ubicado en la parte superior, con el nombre y logo de la aplicación (“🛒 Buscador Inteligente de Productos”).

- **Barra de búsqueda central**  
En el centro de la página, con un placeholder como _“Escribí qué producto estás buscando…”_.

- **Animaciones de carga**  
Mientras el modelo procesa la búsqueda, debe mostrarse una **animación de espera** (por ejemplo, un spinner o barra de progreso).

- **Resultados en tarjetas**
- Los productos deben visualizarse en **tarjetas cuadradas o rectangulares** dentro de un contenedor común, con diseño responsivo.
- Cada tarjeta incluye:
 - **Título del producto**
 - **Precio estimado**
 - **Categoría**
 - **Atributos destacados** (por ejemplo: RAM, GPU, conectividad, marca, etc.)
 - **Etiqueta descriptiva según su scoring:**
   - 🥇 _Más recomendado_ — mayor puntaje  
   - ⭐ _Te podría interesar_ — puntaje medio-alto  
   - 💡 _Similar a tu requerimiento_ — puntaje medio

---

## 🎨 Estilo visual sugerido

- Estética **moderna, minimalista y tecnológica**.  
- Colores suaves con contrastes claros (fondos blancos o grises claros y detalles azules o verdes).  
- Tipografía recomendada: _Poppins_, _Inter_ o _Roboto_.  
- Sombras y microanimaciones sutiles para dar sensación de dinamismo.  
- Diseño **100% responsivo**, adaptado a escritorio, tablet y móvil.