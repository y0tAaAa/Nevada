"""
Создание ярлыка Nevada на рабочем столе
"""

import os
from pathlib import Path

# Windows shortcut creation via registry/command approach
desktop = Path.home() / "Desktop"
shortcut_path = desktop / "Nevada.lnk"
exe_path = Path("c:\\important files\\Nevada\\dist\\Nevada.exe")

# Try using COM
try:
    from win32com.client import Dispatch
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.TargetPath = str(exe_path.resolve())
    shortcut.WorkingDirectory = str(exe_path.parent)
    shortcut.Description = "Nevada — Desktop Assistant"
    shortcut.save()
    print(f"✅ Ярлык создан: {shortcut_path}")
except ImportError:
    # Fallback: create VBS script
    vbs_script = """
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = """ + f'"{desktop}\\Nevada.lnk"' + """
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = """ + f'"{exe_path}"' + """
oLink.WorkingDirectory = """ + f'"{exe_path.parent}"' + """
oLink.Description = "Nevada - Desktop Assistant"
oLink.Save
    """
    
    vbs_path = Path(__file__).parent / "create_shortcut.vbs"
    with open(vbs_path, 'w') as f:
        f.write(vbs_script)
    
    os.system(f'cscript "{vbs_path}"')
    vbs_path.unlink()
    print(f"✅ Ярлык создан: {shortcut_path}")
