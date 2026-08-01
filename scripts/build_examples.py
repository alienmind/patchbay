import subprocess
import sys
import os
import glob

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def print_header(text):
    print(f"\n\033[1;36m{'='*70}\033[0m")
    print(f"\033[1;37m {text} \033[0m")
    print(f"\033[1;36m{'='*70}\033[0m\n")

def run_samples():
    print_header("📦 [1/3] CLASSIFYING SAMPLES")
    cmd = [sys.executable, "scripts/fetch_samples.py", "--apply"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("\033[1;31m❌ Sample classification failed:\033[0m")
        print(result.stdout)
        print(result.stderr)
        sys.exit(result.returncode)
    
    lines = result.stdout.splitlines()
    for line in lines:
        if "copying" in line or "would copy" in line:
            print(f"🎵 \033[1;32m{line.strip()}\033[0m")
        elif "already there" in line:
            print(f"⏩ \033[1;30m{line.strip()}\033[0m")
        elif "not placed" in line:
            print(f"🚫 \033[1;33m{line.strip()}\033[0m")
        elif "UNCLASSIFIED" in line:
            print(f"❓ \033[1;31m{line.strip()}\033[0m")
        elif "decided by:" in line:
            print(f"\n🧠 \033[1;35m{line.strip()}\033[0m")
        elif "copied, logged to" in line:
            print(f"\n✅ \033[1;32m{line.strip()}\033[0m")
        elif line.strip() == "":
            continue
        elif line.startswith("  "):
            print(f"   📁 \033[1;34m{line.strip()}\033[0m")
        else:
            print(f"   {line}")

def get_example_specs():
    specs = []
    for path in glob.glob("examples/*.py"):
        name = os.path.basename(path)
        if name not in ("fetch_samples.py", "build_examples.py"):
            specs.append(path)
    return specs

def has_session(spec_path):
    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()
        return "def SESSION" in content

def run_build():
    specs = get_example_specs()
    for spec in specs:
        print_header(f"🛠️  [2/3] BUILDING RACKS FOR {os.path.basename(spec)}")
        cmd = [sys.executable, "-m", "patchbay.cli", "build", spec, "-o", "build/"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"\033[1;31m❌ Rack build failed for {spec}:\033[0m")
            print(result.stdout)
            print(result.stderr)
            sys.exit(result.returncode)
        
        lines = result.stdout.splitlines()
        rack_name = ""
        for line in lines:
            if "->" in line:
                print(f"🚀 \033[1;32m{line.strip()}\033[0m\n")
            elif not line.startswith("    ") and line.startswith("  "):
                rack_name = line.strip()
            elif "engines:" in line:
                engines = line.strip()
                icon = "🥁"
                if "instrument" in engines:
                    icon = "💿"
                elif "effect" in engines:
                    icon = "🎛️ "
                print(f"  {icon}   \033[1;36m{rack_name:<15}\033[0m \033[3m{engines}\033[0m")
            elif "build\\" in line or "build/" in line:
                pass # skip path output for cleaner ASCII
            elif line.strip():
                print(line)

def run_session():
    specs = get_example_specs()
    for spec in specs:
        if not has_session(spec):
            continue
            
        base = os.path.basename(spec)
        name, _ = os.path.splitext(base)
        out_file = f"build/{name.upper()}.als"
        
        print_header(f"🎛️  [3/3] ASSEMBLING LIVE SET FOR {base}")
        cmd = [sys.executable, "-m", "patchbay.cli", "session", spec, "-o", out_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"\033[1;31m❌ Session build failed for {spec}:\033[0m")
            print(result.stdout)
            print(result.stderr)
            sys.exit(result.returncode)
        
        lines = result.stdout.splitlines()
        for line in lines:
            if "->" in line:
                pass
            elif "track(s)" in line and "return(s)" in line:
                print(f"💿 \033[1;32m{line.strip()}\033[0m\n")
            elif " midi " in line or " audio " in line:
                parts = line.split(maxsplit=2)
                if len(parts) == 3:
                    name, ttype, devices = parts
                    icon = "💿"
                    if "DR" in name.upper() or "DRUM" in name.upper():
                        icon = "🥁"
                    elif ttype == "audio":
                        icon = "🌊"
                    print(f"  {icon}   \033[1;36m{name:<15}\033[0m \033[1;35m{ttype:<7}\033[0m {devices}")
                else:
                    print(f"  {line.strip()}")
            elif " return " in line:
                parts = line.split(maxsplit=2)
                if len(parts) == 3:
                    name, ttype, devices = parts
                    print(f"  🔁   \033[1;33m{name:<15}\033[0m \033[1;35m{ttype:<7}\033[0m {devices}")
                else:
                    print(f"  {line.strip()}")
            elif line.strip():
                print(line)
                
        print(f"\n\033[1;32m✨ All done! Open {out_file} in Live.\033[0m\n")

def main():
    run_samples()
    run_build()
    run_session()

if __name__ == "__main__":
    main()
