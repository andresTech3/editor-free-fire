"""
core/campaign.py
================
Gestor dinámico de campañas de marcas y clientes (Whop Campaigns).
Lee automáticamente cualquier documento de especificaciones (.pdf, .json, .txt, .md, .toml)
en las carpetas 'input/' o 'assets/doc/' y adapta la marca, logo, colores, subtítulos,
llamadas a la acción (CTA) y reglas de edición para la campaña activa.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional


class CampaignManager:
    """
    Parser inteligente de requerimientos y especificaciones de campañas Whop.
    """

    def __init__(self, input_dir: str = "input", config_file: str = "config.toml"):
        self.input_dir = input_dir
        self.config_file = config_file

    def detect_campaign(self) -> Dict[str, Any]:
        """
        Escanea 'input' y 'assets/doc' buscando documentos (.pdf, .json, .txt, .md, .toml).
        Retorna la configuración adaptativa de la campaña activa.
        
        """
        campaign = {
            "brand_name": "Campaña Viral Whop",
            "logo_path": self._find_logo(),
            "logo_position": "top_center",
            "subtitle_style": "viral_yellow",
            "header_color": "#FFD700",
            "accent_color": "#FF0033",
            "cta_text": "Watch the full video on YouTube",
            "target_duration_min": 30.0,
            "target_duration_max": 60.0,
            "custom_hooks": [],
            "source_doc": None,
        }

        # 1. Buscar archivos PDF en assets/doc/ o input/
        pdf_files = list(Path("assets/doc").glob("*.pdf")) + list(Path(self.input_dir).glob("*.pdf"))
        if pdf_files:
            pdf_text = self._extract_pdf_text(str(pdf_files[0]))
            if pdf_text:
                parsed = self._parse_text_brief(pdf_text)
                campaign.update(parsed)
                campaign["source_doc"] = str(pdf_files[0])
                return self._validate_campaign(campaign)

        # 2. Buscar archivos JSON de campaña
        json_files = list(Path(self.input_dir).glob("*.json")) + list(Path(".").glob("campaign*.json"))
        if json_files:
            try:
                with open(json_files[0], "r", encoding="utf-8") as f:
                    data = json.load(f)
                    campaign.update(data)
                    campaign["source_doc"] = str(json_files[0])
                    return self._validate_campaign(campaign)
            except Exception:
                pass

        # 3. Buscar archivos de texto o Markdown (brief.txt, specs.md, instrucc*.txt)
        doc_files = (
            list(Path(self.input_dir).glob("*.txt"))
            + list(Path(self.input_dir).glob("*.md"))
            + list(Path("assets/doc").glob("*.txt"))
            + list(Path("assets/doc").glob("*.md"))
            + list(Path(".").glob("brief*.txt"))
        )

        for doc in doc_files:
            if doc.name.lower() in ["report.txt", "requirements.txt"]:
                continue
            try:
                with open(doc, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    parsed = self._parse_text_brief(content)
                    if parsed:
                        campaign.update(parsed)
                        campaign["source_doc"] = str(doc)
                        return self._validate_campaign(campaign)
            except Exception:
                pass

        return self._validate_campaign(campaign)

    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extrae el texto de un PDF usando pypdf."""
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            full_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
            return "\n".join(full_text)
        except Exception:
            return ""

    def _find_logo(self) -> Optional[str]:
        """Busca el archivo de logo en input/, assets/ o remotion/public/."""
        possible_paths = [
            os.path.join(self.input_dir, "logo.png"),
            os.path.join(self.input_dir, "logo.jpg"),
            os.path.join("assets", "logo.png"),
            os.path.join("remotion", "public", "logo.png"),
            "logo.png",
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return None

    def _parse_text_brief(self, text: str) -> Dict[str, Any]:
        """Extrae reglas de un brief de campaña en texto o PDF."""
        extracted = {}

        # Nombre de Creador / Marca
        if "jesser" in text.lower():
            extracted["brand_name"] = "Jesser x ClipFarm"
        else:
            brand_match = re.search(r"(?:marca|cliente|empresa|brand|campaign):\s*([^\n\r]+)", text, re.IGNORECASE)
            if brand_match:
                extracted["brand_name"] = brand_match.group(1).strip()

        # Estilo de subtítulos / Colores
        if re.search(r"(amarillo|yellow|gold|bold captions)", text, re.IGNORECASE):
            extracted["subtitle_style"] = "viral_yellow"
            extracted["header_color"] = "#FFD700"
        elif re.search(r"(azul|blue|neon)", text, re.IGNORECASE):
            extracted["subtitle_style"] = "neon_blue"
            extracted["header_color"] = "#00E5FF"
        elif re.search(r"(fuego|rojo|red|orange)", text, re.IGNORECASE):
            extracted["subtitle_style"] = "fire_orange"
            extracted["header_color"] = "#FF4500"

        # Pinned Comment / CTA
        cta_match = re.search(r"(?:pinned comment|cta|watch the full video|youtube):\s*([^\n\r]+)", text, re.IGNORECASE)
        if cta_match:
            extracted["cta_text"] = cta_match.group(1).strip()

        return extracted

    def _validate_campaign(self, campaign: Dict[str, Any]) -> Dict[str, Any]:
        """Asegura rutas válidas e imprimibles."""
        if campaign.get("logo_path") and not os.path.exists(campaign["logo_path"]):
            campaign["logo_path"] = self._find_logo()
        return campaign
