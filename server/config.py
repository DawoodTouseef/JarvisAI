from pathlib import Path
from os.path import join as pathjoin,exists as pathexists
from colorama import Fore,init

init(autoreset=True)
backend_dir=Path(__file__).resolve().parent.parent
print(Fore.GREEN+f"Backend dir :{backend_dir}")

cache_dir = Path().home()
jarvis_cache = pathjoin(cache_dir,".jarvis")

print(Fore.GREEN+f" Cache Dir:{jarvis_cache}")
if not pathexists(jarvis_cache):
    from os import makedirs
    print(Fore.RED + f"Cache Dir is not available .Creating it..." )
    makedirs(jarvis_cache,exist_ok=True)
