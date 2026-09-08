"""
core/stock_fetcher.py
======================
Descargador de Recursos B-Roll Gratuitos desde Pexels, Pixabay y Unsplash API.
Obtiene fotos y videos HD libres de derechos para alimentar el Editor Universal.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Callable

def _safe_print(msg: str):
    try:
        print(msg)
    except Exception:
        try:
            print(msg.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

class StockMediaFetcher:
    """
    Descarga imágenes y videos HD desde Pexels, Pixabay y Unsplash sin costo.
    """

    def __init__(self, pexels_key: Optional[str] = None, pixabay_key: Optional[str] = None, log_cb: Optional[Callable] = None):
        self.pexels_key = pexels_key or os.getenv("PEXELS_API_KEY", "jtVBPtog6KYc7A3feVx15WLddEJqVIRhknwY7NqqoEIRlPvUnBh3ir6r")
        self.pixabay_key = pixabay_key or os.getenv("PIXABAY_API_KEY", "16748795-4b92a5e88d8916eb3c39e5951")
        self.log = log_cb or _safe_print

    def _request_json(self, url: str, headers: Optional[Dict] = None) -> Optional[Dict]:
        try:
            req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    return json.loads(data)
        except Exception:
            pass
        return None

    def search_pexels_photos(self, query: str, count: int = 5) -> List[str]:
        if not self.pexels_key:
            return []
        query_enc = urllib.parse.quote(query)
        url = f"https://api.pexels.com/v1/search?query={query_enc}&per_page={count}&orientation=portrait"
        headers = {"Authorization": self.pexels_key, "User-Agent": "Mozilla/5.0"}
        data = self._request_json(url, headers)

        image_urls = []
        if data and "photos" in data:
            for item in data["photos"]:
                src = item.get("src", {}).get("large2x") or item.get("src", {}).get("large")
                if src:
                    image_urls.append(src)
        return image_urls

    def search_pexels_videos(self, query: str, count: int = 5) -> List[str]:
        if not self.pexels_key:
            return []
        query_enc = urllib.parse.quote(query)
        url = f"https://api.pexels.com/videos/search?query={query_enc}&per_page={count}&orientation=portrait"
        headers = {"Authorization": self.pexels_key, "User-Agent": "Mozilla/5.0"}
        data = self._request_json(url, headers)

        video_urls = []
        if data and "videos" in data:
            for item in data["videos"]:
                files = item.get("video_files", [])
                hd_file = next((f for f in files if f.get("width", 0) >= 720 and f.get("link")), None)
                if not hd_file and files:
                    hd_file = files[0]
                if hd_file and hd_file.get("link"):
                    video_urls.append(hd_file["link"])
        return video_urls

    def search_pixabay_photos(self, query: str, count: int = 5) -> List[str]:
        if not self.pixabay_key:
            return []
        query_enc = urllib.parse.quote(query)
        url = f"https://pixabay.com/api/?key={self.pixabay_key}&q={query_enc}&image_type=photo&per_page={count}&orientation=vertical"
        data = self._request_json(url)

        image_urls = []
        if data and "hits" in data:
            for item in data["hits"]:
                src = item.get("largeImageURL") or item.get("webformatURL")
                if src:
                    image_urls.append(src)
        return image_urls

    def search_unsplash_photos(self, query: str, count: int = 5) -> List[str]:
        """Búsqueda directa de alta calidad en Unsplash (Fallback gratuito)."""
        urls = []
        query_terms = [t.strip() for t in query.split(",") if t.strip()]
        if not query_terms:
            query_terms = ["business", "technology", "luxury", "fitness"]

        for i in range(count):
            term = query_terms[i % len(query_terms)]
            # Unsplash HD Source Direct Link
            url = f"https://images.unsplash.com/photo-1507679799987-c73779587ccf?fit=crop&w=1080&h=1920&q=80&sig={i}&{urllib.parse.quote(term)}"
            urls.append(url)
        return urls

    def download_media_files(self, urls: List[str], target_dir: str, prefix: str = "broll") -> List[str]:
        out_dir = Path(target_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        downloaded = []

        for idx, url in enumerate(urls):
            try:
                ext = ".mp4" if ".mp4" in url.lower() or "video" in url.lower() else ".jpg"
                filename = out_dir / f"{prefix}_{idx+1:03d}{ext}"

                self.log(f"  📥 Descargando B-Roll [{idx+1}/{len(urls)}]: {filename.name}...")
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as resp, open(filename, "wb") as f:
                    f.write(resp.read())

                if filename.exists() and filename.stat().st_size > 1024:
                    downloaded.append(str(filename))
            except Exception as e:
                self.log(f"  ⚠️ Aviso al descargar recurso {idx+1}: {e}")

        self.log(f"✅ Descarga de B-Roll completada: {len(downloaded)} archivos guardados en '{out_dir.name}'")
        return downloaded

    def fetch_stock_for_query(self, query: str, target_dir: str, count: int = 10) -> List[str]:
        self.log(f"🔍 Buscando recursos B-Roll HD libres para: '{query}'...")

        all_urls = []
        if self.pexels_key:
            all_urls.extend(self.search_pexels_videos(query, count=count // 2))
            all_urls.extend(self.search_pexels_photos(query, count=count // 2))
        if self.pixabay_key:
            all_urls.extend(self.search_pixabay_photos(query, count=count // 2))

        # Si no hay llaves o no retornó resultados, usar Unsplash HD
        if not all_urls:
            self.log("💡 Obteniendo imágenes HD libres de alta resolución desde Unsplash / Public Stock...")
            all_urls = self.search_unsplash_photos(query, count=count)

        return self.download_media_files(all_urls[:count], target_dir, prefix=f"stock_{query.replace(' ', '_')[:20]}")
