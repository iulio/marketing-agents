import os
import glob

static_dir = os.path.join('app', 'static')
html_files = glob.glob(os.path.join(static_dir, '**', '*.html'), recursive=True)

script_tag = '<script src=\"/bug_reporter.js\" defer></script>'

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if script_tag in content:
        print(f"Already injected in {file_path}")
        continue
        
    if '</body>' in content:
        content = content.replace('</body>', f'{script_tag}\n</body>')
    elif '</html>' in content:
        content = content.replace('</html>', f'{script_tag}\n</html>')
    else:
        content += f'\n{script_tag}'
        
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Injected into {file_path}")
