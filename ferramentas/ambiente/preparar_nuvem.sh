#!/usr/bin/env bash
# Prepara a máquina da nuvem para rodar as FERRAMENTAS do ETIB (mesmas versões do .venv do notebook).
# Uso: bash /mnt/project-files/ferramentas_nuvem/ambiente/preparar_nuvem.sh
# Cria ~/etib-venv (Python 3.11) e instala a ODA File Converter. Menos de 1 min. Pode rodar de novo sem problema.
set -e
git config --global --add safe.directory "*" 2>/dev/null || true
AQUI="$(cd "$(dirname "$0")" && pwd)"
NUVEM="$(dirname "$AQUI")"
VENV="${ETIB_VENV:-$HOME/etib-venv}"
if [ ! -x "$VENV/bin/python" ]; then
  uv venv -q -p python3.11 "$VENV" || uv venv -q -p 3.11 "$VENV"
fi
VIRTUAL_ENV="$VENV" uv pip install -q -r "$AQUI/requirements.txt"
if ! command -v ODAFileConverter >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  (apt-get update -qq || true) >/dev/null 2>&1
  apt-get install -y -qq "$NUVEM/ODAFileConverter_QT6_lnxX64_11dll.deb" libopengl0 libegl1 xvfb libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 libxcb-shape0 libxcb-randr0 libxcb-xfixes0 libxcb-sync1 libxcb-glx0 libfontconfig1 libdbus-1-3 >/dev/null
fi
# LibreOffice: converte a imagem das tabelas do Excel coladas como OLE nas pranchas (render_pdf_nuvem.py)
command -v soffice >/dev/null 2>&1 || apt-get install -y -qq libreoffice-draw-nogui >/dev/null 2>&1 || apt-get install -y -qq libreoffice-draw >/dev/null
mkdir -p "$HOME/.fonts" && cp -n "$NUVEM/pranchas_pdf/fontes/"*.ttf "$HOME/.fonts/" 2>/dev/null || true
echo "ok: $("$VENV/bin/python" -c 'import ifcopenshell,ezdxf,numpy;print("ifcopenshell",ifcopenshell.version,"ezdxf",ezdxf.__version__,"numpy",numpy.__version__)')"
echo "ODA: $(command -v ODAFileConverter)"
