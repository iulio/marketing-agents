import glob

html_files = glob.glob('app/static/*.html')
for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace localStorage with sessionStorage
    content = content.replace('localStorage', 'sessionStorage')
    
    # Fix settingsForm in index.html
    if 'index.html' in file_path:
        content = content.replace(
            '<form id="settingsForm" class="grid grid-cols-1 gap-6 lg:grid-cols-2">',
            '<form id="settingsForm" onsubmit="saveSettings(event)" class="grid grid-cols-1 gap-6 lg:grid-cols-2">'
        )
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print('Replacements complete')
