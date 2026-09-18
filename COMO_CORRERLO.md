# Cómo correr proyectoAPI-s

Guía rápida para levantar el proyecto en tu máquina, sea **Windows, Linux o Mac**. Todo corre
adentro de Docker, así que no hace falta instalar Python ni Node.js a mano.

## 1. Requisitos

- **Docker**:
  - **Windows**: instalá [Docker Desktop](https://www.docker.com/products/docker-desktop/). Te va
    a pedir habilitar WSL2 la primera vez — aceptá y reiniciá si lo pide.
  - **Mac**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) también.
  - **Linux**: `sudo apt install docker.io docker-compose-plugin` (Ubuntu/Debian) o el equivalente
    de tu distro. En algunas distros hace falta agregar tu usuario al grupo `docker`
    (`sudo usermod -aG docker $USER`, después cerrá sesión y volvé a entrar).
- **Git** para clonar el repo.
- Al menos **una API key gratuita** de un proveedor de LLM (paso 3).

Confirmá que Docker esté instalado y corriendo:

```bash
docker --version
docker compose version
```

Si el segundo comando falla con "docker: 'compose' is not a docker command", actualizá Docker
Desktop/Engine a una versión reciente (el plugin `compose` ya viene incluido).

## 2. Clonar el repo

```bash
git clone <URL-del-repo>
cd proyectoAPI-s
```

## 3. Conseguir al menos una API key gratis

El proyecto necesita al menos un proveedor de LLM configurado para funcionar. Los dos confirmados
funcionando sin pedir tarjeta de crédito son:

- **Google Gemini** (recomendado, el más simple de sacar): entrá a
  [aistudio.google.com/apikey](https://aistudio.google.com/apikey), iniciá sesión con una cuenta
  de Google y tocá "Create API key".
- **Groq**: entrá a [console.groq.com/keys](https://console.groq.com/keys), creá una cuenta
  gratuita y tocá "Create API Key".

Con cualquiera de las dos alcanza para probarlo. Cuantas más agregues (Gemini + Groq + OpenAI),
mejor calidad tiene la deliberación multi-LLM, pero no es obligatorio.

## 4. Configurar el `.env`

Copiá el archivo de ejemplo (el `.env` real nunca se sube a git, cada uno tiene el suyo):

- **Mac / Linux** (terminal):
  ```bash
  cp .env.example .env
  ```
- **Windows (PowerShell)**:
  ```powershell
  Copy-Item .env.example .env
  ```
- **Windows (cmd.exe)**:
  ```cmd
  copy .env.example .env
  ```

Abrí `.env` con cualquier editor de texto y completá las keys que conseguiste en el paso 3:

```
GEMINI_API_KEY=tu-key-aca
GROQ_API_KEY=tu-key-aca
```

No hace falta cambiar nada más del archivo para arrancar.

## 5. Levantar todo

Desde la carpeta del proyecto:

```bash
docker compose up --build
```

La primera vez tarda unos minutos (descarga las imágenes base y compila el backend/frontend). Vas
a ver en la terminal los logs de tres servicios: `postgres`, `backend` y `frontend`.

## 6. Usarlo

Con todo arriba (esperá a que los logs se calmen, "Ready" en el frontend y sin errores en el
backend):

- **App**: [http://localhost:3000](http://localhost:3000)
- **API**: [http://localhost:8000](http://localhost:8000)
- **Documentación interactiva de la API** (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

Para apagarlo: `Ctrl+C` en la terminal, y si querés liberar los contenedores del todo,
`docker compose down` (agregá `-v` si además querés borrar los datos de la base).

## Problemas comunes

- **"Cannot connect to the Docker daemon"**: Docker Desktop no está corriendo — abrilo y esperá a
  que el ícono diga que está listo.
- **Puerto ocupado (3000, 8000 o 5432)**: algo más en tu máquina ya usa ese puerto. Cerralo, o
  cambiá el mapeo en `docker-compose.yml` (por ejemplo `"3001:3000"` en vez de `"3000:3000"`).
- **`docker compose` no se reconoce en Windows**: usá una versión reciente de Docker Desktop (ya
  trae el plugin incluido); como alternativa vieja existe `docker-compose` (con guion).
- **El chat responde error 502**: alguna de las API keys en `.env` está vacía, mal copiada (con
  espacios de más) o vencida. Revisá el log del contenedor `backend` en la terminal — ahí aparece
  el error real del proveedor.
- **Cambios en `.env` no se aplican**: hace falta reiniciar los contenedores
  (`docker compose down` y de nuevo `docker compose up --build`), Docker no relee el `.env` en
  caliente.
