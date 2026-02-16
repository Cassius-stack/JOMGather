from PIL import Image, ImageDraw
import os

def create_assets():
    base_dir = r"d:\nyp\WebDE\App_Folder\MySavvyGranny\static\img\filters"
    bg_dir = r"d:\nyp\WebDE\App_Folder\MySavvyGranny\static\img\backgrounds"
    
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    if not os.path.exists(bg_dir):
        os.makedirs(bg_dir)

    # Mustache
    img = Image.new('RGBA', (200, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw handlebar mustache
    draw.chord([(20, 20), (180, 80)], 0, 180, fill='black')
    img.save(os.path.join(base_dir, 'mustache.png'))

    # Hat
    img = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.polygon([(50, 150), (150, 150), (100, 20)], fill='red', outline='black')
    img.save(os.path.join(base_dir, 'hat.png'))

    # Glasses
    img = Image.new('RGBA', (300, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([(20, 20), (120, 80)], fill=(0, 0, 0, 150), outline='black')
    draw.ellipse([(180, 20), (280, 80)], fill=(0, 0, 0, 150), outline='black')
    draw.line([(120, 50), (180, 50)], fill='black', width=5)
    img.save(os.path.join(base_dir, 'glasses.png'))

    # Background (Beach)
    img = Image.new('RGB', (640, 480), 'skyblue')
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 300), (640, 480)], fill='yellow') # Sand
    draw.rectangle([(0, 240), (640, 300)], fill='blue') # Water
    img.save(os.path.join(bg_dir, 'beach.jpg'))
    
    # Background (Office)
    img = Image.new('RGB', (640, 480), 'lightgray')
    draw = ImageDraw.Draw(img)
    draw.rectangle([(50, 50), (200, 200)], fill='white', outline='black') # Window
    draw.rectangle([(400, 100), (600, 400)], fill='brown') # Bookshelf
    img.save(os.path.join(bg_dir, 'office.jpg'))

    print("Assets created.")

if __name__ == "__main__":
    create_assets()
