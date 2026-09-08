"""
deploy_huggingface.py — 1-Click Cloud Deployment to Hugging Face Spaces (24/7 Free Hosting)
"""
import os
import sys
import webbrowser
from pathlib import Path
from huggingface_hub import HfApi, login

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

def main():
    print("=" * 75)
    print("🚀 DESPLEGAR CÓDIGO HEADSHOT A HUGGING FACE SPACES (24/7 NUBE GRATIS)")
    print("=" * 75)
    print()

    # 1. Check for existing Hugging Face Token
    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token) if token else HfApi()

    user_info = None
    try:
        user_info = api.whoami()
    except Exception:
        pass

    if not user_info:
        print("🔑 Se necesita un Token de Acceso de Hugging Face (con permiso 'Write').")
        print("   Si no lo tienes, créalo gratis en 10 segundos aquí:")
        print("   👉  https://huggingface.co/settings/tokens\n")
        
        webbrowser.open("https://huggingface.co/settings/tokens")
        user_token = input("Pega tu Token de Hugging Face (hf_...): ").strip()
        if not user_token:
            print("❌ No se ingresó ningún token. Cancelando despliegue.")
            return

        login(token=user_token, add_to_git_credential=True)
        api = HfApi(token=user_token)
        try:
            user_info = api.whoami()
        except Exception as e:
            print(f"❌ Error al autenticar con Hugging Face: {e}")
            return

    username = user_info.get("name") or user_info.get("username")
    print(f"\n✅ Conectado como usuario de Hugging Face: {username}")

    # 2. Create Space Repository
    space_name = "codigo-headshot-studio"
    repo_id = f"{username}/{space_name}"
    print(f"\n📦 Configurando Space: {repo_id} (Docker 24/7)...")

    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            exist_ok=True
        )
        print(f"✅ Space listo: https://huggingface.co/spaces/{repo_id}")
    except Exception as e:
        print(f"⚠️ Aviso al verificar repositorio: {e}")

    # 3. Upload Project Files (Excluding massive local video cache)
    print("\n🚀 Subiendo archivos del proyecto al Space en la nube...")
    ignore_list = [
        "output/*",
        "temp_uploads/*",
        "scratch/*",
        ".git/*",
        ".gemini/*",
        ".env",
        "*.onnx",
        "__pycache__/*",
        "*.bat",
        "web_studio/.vercel/*",
        "node_modules/*"
    ]

    try:
        api.upload_folder(
            folder_path=str(PROJECT_ROOT),
            repo_id=repo_id,
            repo_type="space",
            ignore_patterns=ignore_list,
            commit_message="Deploy Codigo Headshot Studio 24/7 Cloud Backend"
        )
        print("✅ Archivos subidos con éxito.")
    except Exception as e:
        print(f"❌ Error durante la subida: {e}")
        return

    # 4. URLs
    space_url = f"https://huggingface.co/spaces/{repo_id}"
    direct_app_url = f"https://{username.lower()}-{space_name.lower()}.hf.space"

    print("\n" + "═" * 75)
    print("🎉 ¡DESPLIEGUE A HUGGING FACE SPACES COMPLETADO!")
    print("═" * 75)
    print(f"🌐 Panel de Control del Space: {space_url}")
    print(f"⚡ Enlace Directo 24/7 (Abierto para Todo el Mundo):")
    print(f"👉  {direct_app_url}")
    print("═" * 75)
    print("\nCualquier persona en el mundo puede entrar a ese enlace y crear videos")
    print("sin que dependa de tu computadora ni de que la tengas encendida.")
    print()

    webbrowser.open(space_url)

if __name__ == "__main__":
    main()
