from PIL import Image

for i in range(1, 19):
    img = Image.open(f'../assets/event_cards/good/{i}.png')
    img.rotate(180).save(f'../assets/event_cards/bad/{i}.png')
    print(f'Done: {i}.png')
