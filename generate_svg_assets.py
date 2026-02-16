import os

def create_svgs():
    base_dir = r"d:\nyp\WebDE\App_Folder\MySavvyGranny\static\img\filters"
    bg_dir = r"d:\nyp\WebDE\App_Folder\MySavvyGranny\static\img\backgrounds"
    
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    if not os.path.exists(bg_dir):
        os.makedirs(bg_dir)

    # Mustache SVG
    mustache_svg = '''<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">
    <path d="M20,20 Q100,80 180,20 Q150,50 100,50 Q50,50 20,20 Z" fill="black"/>
</svg>'''
    with open(os.path.join(base_dir, 'mustache.svg'), 'w') as f:
        f.write(mustache_svg)

    # Hat SVG
    hat_svg = '''<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
    <polygon points="50,150 150,150 100,20" fill="red" stroke="black" stroke-width="2"/>
    <rect x="30" y="150" width="140" height="20" fill="darkred"/>
</svg>'''
    with open(os.path.join(base_dir, 'hat.svg'), 'w') as f:
        f.write(hat_svg)

    # Glasses SVG
    glasses_svg = '''<svg width="300" height="100" xmlns="http://www.w3.org/2000/svg">
    <circle cx="70" cy="50" r="40" fill="rgba(0,0,0,0.5)" stroke="black" stroke-width="5"/>
    <circle cx="230" cy="50" r="40" fill="rgba(0,0,0,0.5)" stroke="black" stroke-width="5"/>
    <line x1="110" y1="50" x2="190" y2="50" stroke="black" stroke-width="5"/>
</svg>'''
    with open(os.path.join(base_dir, 'glasses.svg'), 'w') as f:
        f.write(glasses_svg)

    # Beach BG (SVG) - Simple gradient
    beach_svg = '''<svg width="640" height="480" xmlns="http://www.w3.org/2000/svg">
    <rect width="640" height="480" fill="#87CEEB"/>
    <rect y="300" width="640" height="180" fill="#F4A460"/>
    <circle cx="50" cy="50" r="30" fill="yellow"/>
</svg>'''
    with open(os.path.join(bg_dir, 'beach.svg'), 'w') as f:
        f.write(beach_svg)
        
    # Office BG (SVG)
    office_svg = '''<svg width="640" height="480" xmlns="http://www.w3.org/2000/svg">
    <rect width="640" height="480" fill="#D3D3D3"/>
    <rect x="50" y="50" width="200" height="200" fill="white" stroke="black"/>
    <rect x="400" y="100" width="200" height="300" fill="#8B4513"/>
</svg>'''
    with open(os.path.join(bg_dir, 'office.svg'), 'w') as f:
        f.write(office_svg)

    print("SVG Assets created.")

if __name__ == "__main__":
    create_svgs()
