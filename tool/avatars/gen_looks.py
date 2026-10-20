"""Generate the 100 female + 100 male Hoola avatar looks -> assets/santosh3d/looks.js + server/app/avatar/looks.json.

Deterministic (fixed seed). Every look is checked against every other: they must differ in at least
MIN_DIFF of the visible features below, and no two may share hair style + hair colour + outfit.
Run:  python3 tool/avatars/gen_looks.py
"""
import json, random, os, itertools

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIN_DIFF = 5

SKIN = ['#f7dccb', '#f2cfb3', '#ecc19f', '#e1b08a', '#d39c74', '#c98a62', '#b97a52', '#a46b47', '#8d5a3b', '#7a4a30', '#633b27', '#4f2e1f']
HAIR = {'black': '#141010', 'softblack': '#231a15', 'darkbrown': '#3a2418', 'brown': '#5a3a24', 'chestnut': '#7a4a2a',
        'auburn': '#8e3b22', 'ginger': '#c0562a', 'honey': '#b8863b', 'blonde': '#d9b25c', 'platinum': '#e3d6b0',
        'silver': '#a9a7a4', 'pink': '#e26aa0', 'lavender': '#9b7fd1', 'teal': '#2a9d8f', 'blueblack': '#1b2233', 'plum': '#5e2a4a'}
EYES = {'darkbrown': '#2a1810', 'brown': '#3e2414', 'hazel': '#6b4a22', 'amber': '#8a5a1c', 'green': '#2f5d3a', 'blue': '#3d6aa8', 'grey': '#6c7a86'}
LIPS = ['#b04a4a', '#c0505a', '#a83a3a', '#8c2f39', '#d0606a', '#9c3d4a', '#c4565e', '#7a2a2a', '#b85a5a', '#d47a7a', '#a14450', '#6e2424']
COL = ['#e8558a', '#f29418', '#3f51b5', '#2bb3a3', '#c2185b', '#7b5ea7', '#ffd54f', '#00897b', '#d84315', '#4a78b8', '#2f3b52', '#f2e3c9',
       '#6b8f71', '#e57373', '#8d6e63', '#26a69a', '#ab47bc', '#ef6c00', '#5c6bc0', '#9ccc65', '#f06292', '#455a64', '#ffb300', '#1e88e5',
       '#b71c1c', '#004d40', '#f4511e', '#795548', '#80cbc4', '#ce93d8', '#ffffff', '#212121', '#a1887f', '#ff8a65']
SCARF = ['#6b8f71', '#2f3b52', '#c2185b', '#8d6e63', '#7b5ea7', '#e8b4b8', '#455a64', '#b39ddb', '#004d40', '#d7ccc8', '#5d4037', '#90a4ae']
WRAPC = ['#e65100', '#00897b', '#6a1b9a', '#c62828', '#f9a825', '#1565c0', '#2e7d32', '#ad1457']
OPEN_HAIR = ['long', 'bangs', 'halfup', 'wavy', 'bob', 'pixie', 'pony_high', 'pony_low', 'bun', 'bun_low', 'buns', 'braid', 'braids',
             'braid_back', 'afro', 'puffs', 'curly', 'curly_short', 'shoulder', 'sidepart']
TOPS = ['puffer', 'hoodie', 'track', 'blazer', 'sweater', 'denim', 'wrap', 'kurta']
GLASSES = ['round', 'cat', 'square', 'thin', 'big']

# name, city, country, region, skin index range, hair colour pool, special
PEOPLE = [
 ('Priya', 'Pune', 'India', 'sa', (3, 8), 'dark', {'top': 'kurta'}), ('Ananya', 'Bengaluru', 'India', 'sa', (3, 8), 'dark', {}),
 ('Meera', 'Jaipur', 'India', 'sa', (3, 8), 'dark', {'top': 'saree', 'hair': 'braid_back'}), ('Kavya', 'Chennai', 'India', 'sa', (5, 10), 'dark', {'top': 'saree', 'hair': 'bun_low'}),
 ('Riya', 'Mumbai', 'India', 'sa', (3, 8), 'dark', {}), ('Sneha', 'Kolkata', 'India', 'sa', (4, 9), 'dark', {'top': 'saree'}),
 ('Aisha', 'Hyderabad', 'India', 'sa', (4, 9), 'dark', {'hair': 'hijab'}), ('Gurpreet', 'Amritsar', 'India', 'sa', (2, 6), 'dark', {'top': 'kurta', 'hair': 'braid'}),
 ('Lalita', 'Akola', 'India', 'sa', (5, 9), 'dark', {'top': 'saree', 'hair': 'bun', 'old': True}), ('Nisha', 'Delhi', 'India', 'sa', (3, 7), 'dark', {}),
 ('Deepa', 'Kochi', 'India', 'sa', (6, 10), 'dark', {'hair': 'braid_back', 'top': 'kurta'}), ('Pooja', 'Ahmedabad', 'India', 'sa', (3, 7), 'dark', {}),
 ('Tanvi', 'Nagpur', 'India', 'sa', (4, 9), 'dark', {}), ('Mitali', 'Guwahati', 'India', 'sa', (2, 6), 'dark', {}),
 ('Sana', 'Lucknow', 'India', 'sa', (3, 7), 'dark', {'top': 'kurta'}),
 ('Farah', 'Lahore', 'Pakistan', 'sa', (3, 7), 'dark', {'top': 'kurta'}), ('Nusrat', 'Dhaka', 'Bangladesh', 'sa', (5, 9), 'dark', {'hair': 'hijab'}),
 ('Sajani', 'Kathmandu', 'Nepal', 'sa', (2, 7), 'dark', {}), ('Tharushi', 'Colombo', 'Sri Lanka', 'sa', (6, 10), 'dark', {'top': 'saree'}),
 ('Pema', 'Thimphu', 'Bhutan', 'sa', (2, 6), 'dark', {}),
 ('Yuki', 'Osaka', 'Japan', 'ea', (0, 3), 'darkdye', {}), ('Hana', 'Tokyo', 'Japan', 'ea', (0, 3), 'darkdye', {}),
 ('Mei', 'Shanghai', 'China', 'ea', (0, 3), 'dark', {}), ('Lin', 'Taipei', 'Taiwan', 'ea', (0, 3), 'dark', {}),
 ('Ji-woo', 'Seoul', 'South Korea', 'ea', (0, 2), 'darkdye', {}), ('Seo-yeon', 'Busan', 'South Korea', 'ea', (0, 3), 'dark', {}),
 ('Xiaoyu', 'Chengdu', 'China', 'ea', (0, 3), 'dark', {}), ('Sarnai', 'Ulaanbaatar', 'Mongolia', 'ea', (2, 5), 'dark', {}),
 ('Wing', 'Hong Kong', 'China', 'ea', (0, 3), 'dark', {'old': True}), ('Aiko', 'Kyoto', 'Japan', 'ea', (0, 2), 'dark', {}),
 ('Linh', 'Hanoi', 'Vietnam', 'sea', (1, 5), 'dark', {}), ('Mai', 'Ho Chi Minh City', 'Vietnam', 'sea', (2, 6), 'dark', {}),
 ('Siti', 'Kuala Lumpur', 'Malaysia', 'sea', (3, 7), 'dark', {'hair': 'hijab'}), ('Putri', 'Jakarta', 'Indonesia', 'sea', (4, 8), 'dark', {'hair': 'hijab'}),
 ('Maria', 'Manila', 'Philippines', 'sea', (3, 7), 'dark', {}), ('Nok', 'Bangkok', 'Thailand', 'sea', (2, 6), 'dark', {}),
 ('Sopheap', 'Phnom Penh', 'Cambodia', 'sea', (4, 8), 'dark', {}), ('Thiri', 'Yangon', 'Myanmar', 'sea', (3, 7), 'dark', {}),
 ('Layla', 'Dubai', 'UAE', 'me', (2, 6), 'dark', {'hair': 'hijab'}), ('Noor', 'Amman', 'Jordan', 'me', (1, 5), 'darkbrown', {}),
 ('Zeynep', 'Istanbul', 'Türkiye', 'me', (1, 4), 'brownish', {}), ('Shirin', 'Tehran', 'Iran', 'me', (1, 5), 'darkbrown', {}),
 ('Yasmin', 'Cairo', 'Egypt', 'me', (3, 7), 'dark', {'hair': 'hijab'}), ('Reem', 'Riyadh', 'Saudi Arabia', 'me', (3, 7), 'dark', {'hair': 'hijab', 'old': True}),
 ('Aigerim', 'Almaty', 'Kazakhstan', 'me', (1, 4), 'dark', {}), ('Dilnoza', 'Tashkent', 'Uzbekistan', 'me', (1, 5), 'dark', {}),
 ('Amara', 'Lagos', 'Nigeria', 'af', (8, 11), 'dark', {'hair': 'wrap'}), ('Adaeze', 'Abuja', 'Nigeria', 'af', (8, 11), 'darkdye', {}),
 ('Akosua', 'Accra', 'Ghana', 'af', (9, 11), 'dark', {'hair': 'wrap'}), ('Fatou', 'Dakar', 'Senegal', 'af', (10, 11), 'dark', {'hair': 'turban'}),
 ('Wanjiru', 'Nairobi', 'Kenya', 'af', (9, 11), 'dark', {}), ('Zawadi', 'Dar es Salaam', 'Tanzania', 'af', (9, 11), 'dark', {}),
 ('Thandiwe', 'Johannesburg', 'South Africa', 'af', (8, 11), 'darkdye', {}), ('Naledi', 'Cape Town', 'South Africa', 'af', (7, 10), 'dark', {}),
 ('Selam', 'Addis Ababa', 'Ethiopia', 'af', (7, 10), 'dark', {}), ('Imani', 'Kampala', 'Uganda', 'af', (9, 11), 'dark', {'old': True}),
 ('Aminata', 'Bamako', 'Mali', 'af', (10, 11), 'dark', {'hair': 'turban'}), ('Salma', 'Casablanca', 'Morocco', 'af', (3, 7), 'darkbrown', {}),
 ('Nia', 'Kigali', 'Rwanda', 'af', (9, 11), 'dark', {}), ('Chipo', 'Harare', 'Zimbabwe', 'af', (9, 11), 'dark', {}),
 ('Sofia', 'Madrid', 'Spain', 'eu', (1, 4), 'brownish', {}), ('Giulia', 'Rome', 'Italy', 'eu', (1, 4), 'brownish', {}),
 ('Chloé', 'Paris', 'France', 'eu', (0, 3), 'any', {}), ('Emma', 'Berlin', 'Germany', 'eu', (0, 2), 'light', {}),
 ('Freya', 'Oslo', 'Norway', 'eu', (0, 1), 'light', {}), ('Saoirse', 'Dublin', 'Ireland', 'eu', (0, 1), 'red', {}),
 ('Olivia', 'London', 'UK', 'eu', (0, 11), 'any', {}), ('Inês', 'Lisbon', 'Portugal', 'eu', (1, 4), 'brownish', {}),
 ('Anna', 'Warsaw', 'Poland', 'eu', (0, 2), 'light', {}), ('Elena', 'Athens', 'Greece', 'eu', (1, 4), 'brownish', {'old': True}),
 ('Lotte', 'Amsterdam', 'Netherlands', 'eu', (0, 2), 'light', {}), ('Maja', 'Stockholm', 'Sweden', 'eu', (0, 1), 'light', {}),
 ('Aino', 'Helsinki', 'Finland', 'eu', (0, 1), 'light', {}), ('Katya', 'Kyiv', 'Ukraine', 'eu', (0, 2), 'any', {}),
 ('Zsófia', 'Budapest', 'Hungary', 'eu', (0, 3), 'any', {}), ('Isla', 'Edinburgh', 'Scotland', 'eu', (0, 1), 'red', {}),
 ('Emily', 'New York', 'USA', 'am', (0, 11), 'any', {}), ('Jasmine', 'Atlanta', 'USA', 'am', (8, 11), 'darkdye', {}),
 ('Mia', 'Los Angeles', 'USA', 'am', (0, 6), 'any', {}), ('Aiyana', 'Phoenix', 'USA', 'am', (5, 8), 'dark', {}),
 ('Camila', 'Mexico City', 'Mexico', 'am', (3, 7), 'brownish', {}), ('Valentina', 'Bogotá', 'Colombia', 'am', (2, 7), 'brownish', {}),
 ('Lucía', 'Buenos Aires', 'Argentina', 'am', (1, 4), 'any', {}), ('Gabriela', 'São Paulo', 'Brazil', 'am', (2, 9), 'any', {}),
 ('Ana', 'Rio de Janeiro', 'Brazil', 'am', (6, 10), 'brownish', {}), ('Isabella', 'Lima', 'Peru', 'am', (4, 8), 'dark', {}),
 ('Daniela', 'Santiago', 'Chile', 'am', (1, 5), 'any', {}), ('Keisha', 'Kingston', 'Jamaica', 'am', (9, 11), 'dark', {}),
 ('Marisol', 'Havana', 'Cuba', 'am', (4, 9), 'brownish', {'old': True}), ('Chloe', 'Toronto', 'Canada', 'am', (0, 11), 'any', {}),
 ('Sarah', 'Vancouver', 'Canada', 'am', (0, 3), 'any', {}), ('Aaliyah', 'Chicago', 'USA', 'am', (8, 11), 'darkdye', {}),
 ('Nayeli', 'Oaxaca', 'Mexico', 'am', (5, 8), 'dark', {}), ('Inés', 'Quito', 'Ecuador', 'am', (4, 8), 'dark', {}),
 ('Ruby', 'Sydney', 'Australia', 'oc', (0, 3), 'any', {}), ('Charlotte', 'Melbourne', 'Australia', 'oc', (0, 2), 'light', {}),
 ('Aroha', 'Auckland', 'New Zealand', 'oc', (5, 9), 'dark', {}), ('Leilani', 'Honolulu', 'USA', 'oc', (4, 8), 'dark', {}),
 ('Losana', 'Suva', 'Fiji', 'oc', (8, 11), 'dark', {}), ('Mele', "Nuku'alofa", 'Tonga', 'oc', (7, 10), 'dark', {}),
]
assert len(PEOPLE) == 100, len(PEOPLE)
POOLS = {'dark': ['black', 'softblack', 'darkbrown', 'blueblack'], 'darkdye': ['black', 'softblack', 'darkbrown', 'plum', 'pink', 'lavender', 'teal', 'blueblack'],
         'darkbrown': ['softblack', 'darkbrown', 'brown', 'chestnut'], 'brownish': ['darkbrown', 'brown', 'chestnut', 'auburn', 'honey'],
         'light': ['blonde', 'platinum', 'honey', 'brown', 'chestnut'], 'red': ['ginger', 'auburn', 'chestnut'],
         'any': ['black', 'darkbrown', 'brown', 'chestnut', 'auburn', 'ginger', 'honey', 'blonde', 'platinum', 'pink', 'lavender', 'teal']}
CURLY = {'afro', 'puffs', 'curly', 'curly_short'}

def make(rng, i, person):
    name, city, country, region, (s0, s1), pool, sp = person
    skin = rng.randint(s0, s1)
    old = sp.get('old')
    hs = sp.get('hair')
    if not hs:
        opts = list(OPEN_HAIR)
        if region == 'af' or (region == 'am' and skin >= 8): opts += ['afro', 'puffs', 'curly', 'curly_short', 'braids', 'braid'] * 2
        elif region in ('ea', 'sea'): opts = [o for o in opts if o not in CURLY]
        if old: opts = ['bun', 'bun_low', 'bob', 'pixie', 'shoulder', 'curly_short']
        hs = rng.choice(opts)
    if hs == 'hijab': hc = rng.choice(SCARF)
    elif hs in ('wrap', 'turban'): hc = rng.choice(WRAPC)
    else: hc = HAIR['silver'] if old else HAIR[rng.choice(POOLS[pool])]
    top = sp.get('top') or rng.choice(TOPS if region == 'sa' else [t for t in TOPS if t != 'kurta'])
    tc, tc2 = rng.sample(COL, 2)
    if top in ('saree',): bottom = {'style': 'long', 'color': tc, 'color2': rng.choice(['#f4b400', '#d9a441', tc2])}
    elif top == 'kurta': bottom = {'style': rng.choice(['pants', 'leggings']), 'color': rng.choice([tc2, '#f4f1ea', '#212121'])}
    elif hs == 'hijab': bottom = {'style': rng.choice(['long', 'long', 'pants']), 'color': rng.choice(COL), 'color2': rng.choice(COL)}
    else:
        bs = rng.choice(['pants', 'jeans', 'jeans', 'skirt', 'leggings', 'long'] + (['long'] if old else []))
        bottom = {'style': bs, 'color': rng.choice(['#3b5b8c', '#24477a', '#2c3566']) if bs == 'jeans' else rng.choice(COL + ['#2a2a33', '#37474f', '#3e2723'])}
        if bs == 'skirt' and rng.random() < .4: bottom['legs'] = rng.choice(['#212121', '#4e342e', '#f8bbd0', '#90caf9'])
        if bs == 'long': bottom['color2'] = rng.choice(COL)
    acc = []
    if region == 'sa' and rng.random() < .65: acc.append('bindi')
    if region == 'sa' and rng.random() < .35: acc.append(rng.choice(['nosestud', 'nosering']))
    acc.append(rng.choice(['studs', 'hoops', 'drops', 'jhumka' if region == 'sa' else 'studs', None, None]))
    if rng.random() < .3: acc.append('necklace');
    if 'necklace' in acc and rng.random() < .5: acc.append('pearls')
    if region == 'sa' and rng.random() < .4: acc.append('bangles')
    if rng.random() < .15: acc.append('watch')
    if skin <= 2 and pool in ('red', 'light', 'any') and rng.random() < .45: acc.append('freckles')
    if rng.random() < .1: acc.append('mole')
    if hs not in ('hijab', 'wrap', 'turban', 'afro'):
        if rng.random() < .18: acc.append('headband')
        elif rng.random() < .15: acc.append('clip')
        elif rng.random() < .12: acc.append('flower')
    if hs in ('bun', 'bun_low', 'braid_back') and region == 'sa' and rng.random() < .7: acc.append('gajra')
    if hs in ('bun', 'hijab') and rng.random() < .3: acc.append('pin')
    if top == 'saree' and rng.random() < .3: acc.append('tikka')
    if top in ('sweater', 'blazer', 'denim') and rng.random() < .2: acc.append('scarf')
    if rng.random() < .15: acc.append('sling')
    if hs != 'hijab' and not ({'studs', 'hoops', 'drops', 'jhumka'} & set(acc)) and rng.random() < .75:
        acc.append(rng.choice(['studs', 'studs', 'hoops', 'drops']))
    acc = sorted(set(a for a in acc if a))
    glasses = {'style': 'none'}
    if old or rng.random() < .42:
        g = rng.choice(GLASSES + (['thin', 'round'] if old else []))
        glasses = {'style': g, 'color': '#c9a24a' if g == 'thin' else rng.choice(['#141416', '#5a2d1a', '#d81b60', '#1e88e5', '#7b1fa2', '#c9a24a', '#00796b', '#8d6e63'])}
    look = {
        'id': 'f%03d' % (i + 1), 'name': name, 'city': city, 'country': country, 'region': region, 'gender': 'f',
        'skin': SKIN[skin], 'eyes': EYES[rng.choice(['darkbrown', 'brown', 'brown', 'hazel', 'amber'] + (['green', 'blue', 'grey', 'blue', 'green'] if pool in ('light', 'red') else ['green'] if pool in ('any', 'brownish') else []))],
        'lips': rng.choice(LIPS), 'hair': {'style': hs, 'color': hc}, 'glasses': glasses,
        'top': {'style': top, 'color': tc, 'color2': tc2}, 'bottom': bottom,
        'shoes': rng.choice(['#f7f5f2', '#f7f5f2', '#212121', '#e8558a', '#ffd54f', '#90caf9', '#a1887f', '#ffffff']),
        'laces': rng.choice(COL), 'phone': rng.choice(['#26272c', '#26272c', '#e8558a', '#b39ddb', '#80cbc4', '#ffcc80', '#c5e1a5', '#90a4ae']),
        'acc': acc, 'accColor': rng.choice(['#c2185b', '#b71c1c', '#1565c0', '#2e7d32', '#6a1b9a', '#ff6f00', '#00838f', '#ad1457']),
    }
    if hs not in ('hijab', 'wrap', 'turban'): look['hair']['part'] = rng.choice(['c', 'c', 'l', 'r'])
    if top == 'puffer' and rng.random() < .55 or rng.random() < .12: look['straps'] = rng.choice(['#27358c', '#212121', '#ff7043', '#00897b', '#6a1b9a', '#f9a825'])
    if 'flower' in acc or 'gajra' in acc: look['flower'] = '#fbfbf7' if 'gajra' in acc else rng.choice(['#f48fb1', '#fff59d', '#ffffff', '#ff8a65'])
    if old: look['scale'] = .95; look['old'] = True
    else: look['scale'] = round(rng.uniform(.96, 1.02), 3)
    return look

def feats(l):
    return [l['hair']['style'], l['hair']['color'], l['skin'], l['eyes'], l['top']['style'], l['top']['color'], l['top']['color2'],
            l['bottom']['style'], l['bottom']['color'], l['glasses']['style'], tuple(l['acc']), l.get('straps')]

def diff(a, b): return sum(x != y for x, y in zip(feats(a), feats(b)))

# ---------------------------------------------------------------- men (v0.52), own seed so the women never change
MEN = [
 ('Rahul', 'Pune', 'India', 'sa', (3, 8), 'dark', {}), ('Arjun', 'Bengaluru', 'India', 'sa', (3, 8), 'dark', {}),
 ('Vikram', 'Jaipur', 'India', 'sa', (3, 8), 'dark', {'top': 'kurta', 'mustache': 'handlebar'}), ('Karthik', 'Chennai', 'India', 'sa', (5, 10), 'dark', {}),
 ('Rohan', 'Mumbai', 'India', 'sa', (3, 8), 'dark', {}), ('Sourav', 'Kolkata', 'India', 'sa', (4, 9), 'dark', {'top': 'kurta'}),
 ('Imran', 'Hyderabad', 'India', 'sa', (4, 9), 'dark', {'hair': 'kufi', 'beard': 'full'}), ('Harpreet', 'Amritsar', 'India', 'sa', (2, 6), 'dark', {'hair': 'dastar', 'beard': 'full'}),
 ('Ganesh', 'Akola', 'India', 'sa', (5, 9), 'dark', {'top': 'kurta', 'mustache': 'thick', 'old': True}), ('Aman', 'Delhi', 'India', 'sa', (3, 7), 'dark', {}),
 ('Anoop', 'Kochi', 'India', 'sa', (6, 10), 'dark', {'mustache': 'thick'}), ('Jignesh', 'Ahmedabad', 'India', 'sa', (3, 7), 'dark', {}),
 ('Sachin', 'Nagpur', 'India', 'sa', (4, 9), 'dark', {}), ('Bhaskar', 'Guwahati', 'India', 'sa', (2, 6), 'dark', {}),
 ('Faizan', 'Lucknow', 'India', 'sa', (3, 7), 'dark', {'top': 'kurta', 'beard': 'short'}),
 ('Usman', 'Lahore', 'Pakistan', 'sa', (3, 7), 'dark', {'top': 'kurta', 'beard': 'full'}), ('Tanvir', 'Dhaka', 'Bangladesh', 'sa', (5, 9), 'dark', {}),
 ('Bikash', 'Kathmandu', 'Nepal', 'sa', (2, 7), 'dark', {}), ('Kasun', 'Colombo', 'Sri Lanka', 'sa', (6, 10), 'dark', {}),
 ('Tshering', 'Thimphu', 'Bhutan', 'sa', (2, 6), 'dark', {}),
 ('Haruto', 'Osaka', 'Japan', 'ea', (0, 3), 'darkdye', {}), ('Kenji', 'Tokyo', 'Japan', 'ea', (0, 3), 'dark', {'old': True}),
 ('Wei', 'Shanghai', 'China', 'ea', (0, 3), 'dark', {}), ('Chen', 'Taipei', 'Taiwan', 'ea', (0, 3), 'dark', {}),
 ('Min-jun', 'Seoul', 'South Korea', 'ea', (0, 2), 'darkdye', {}), ('Ji-ho', 'Busan', 'South Korea', 'ea', (0, 3), 'dark', {}),
 ('Hao', 'Chengdu', 'China', 'ea', (0, 3), 'dark', {}), ('Bat-Erdene', 'Ulaanbaatar', 'Mongolia', 'ea', (2, 5), 'dark', {}),
 ('Ka-ho', 'Hong Kong', 'China', 'ea', (0, 3), 'dark', {}), ('Ren', 'Kyoto', 'Japan', 'ea', (0, 2), 'dark', {}),
 ('Minh', 'Hanoi', 'Vietnam', 'sea', (1, 5), 'dark', {}), ('Tuan', 'Ho Chi Minh City', 'Vietnam', 'sea', (2, 6), 'dark', {}),
 ('Hafiz', 'Kuala Lumpur', 'Malaysia', 'sea', (3, 7), 'dark', {'hair': 'kufi'}), ('Budi', 'Jakarta', 'Indonesia', 'sea', (4, 8), 'dark', {}),
 ('Jose', 'Manila', 'Philippines', 'sea', (3, 7), 'dark', {}), ('Somchai', 'Bangkok', 'Thailand', 'sea', (2, 6), 'dark', {}),
 ('Dara', 'Phnom Penh', 'Cambodia', 'sea', (4, 8), 'dark', {}), ('Aung', 'Yangon', 'Myanmar', 'sea', (3, 7), 'dark', {}),
 ('Khalid', 'Dubai', 'UAE', 'me', (2, 6), 'dark', {'hair': 'ghutra', 'top': 'thobe', 'beard': 'short'}), ('Omar', 'Amman', 'Jordan', 'me', (1, 5), 'darkbrown', {}),
 ('Emre', 'Istanbul', 'Türkiye', 'me', (1, 4), 'brownish', {}), ('Reza', 'Tehran', 'Iran', 'me', (1, 5), 'darkbrown', {}),
 ('Karim', 'Cairo', 'Egypt', 'me', (3, 7), 'dark', {}), ('Faisal', 'Riyadh', 'Saudi Arabia', 'me', (3, 7), 'dark', {'hair': 'ghutra', 'top': 'thobe', 'beard': 'full', 'old': True}),
 ('Nurlan', 'Almaty', 'Kazakhstan', 'me', (1, 4), 'dark', {}), ('Jasur', 'Tashkent', 'Uzbekistan', 'me', (1, 5), 'dark', {}),
 ('Chinedu', 'Lagos', 'Nigeria', 'af', (8, 11), 'dark', {}), ('Emeka', 'Abuja', 'Nigeria', 'af', (8, 11), 'dark', {'hair': 'kufi'}),
 ('Kwame', 'Accra', 'Ghana', 'af', (9, 11), 'dark', {}), ('Moussa', 'Dakar', 'Senegal', 'af', (10, 11), 'dark', {}),
 ('Otieno', 'Nairobi', 'Kenya', 'af', (9, 11), 'dark', {}), ('Baraka', 'Dar es Salaam', 'Tanzania', 'af', (9, 11), 'dark', {}),
 ('Sipho', 'Johannesburg', 'South Africa', 'af', (8, 11), 'darkdye', {}), ('Thabo', 'Cape Town', 'South Africa', 'af', (7, 10), 'dark', {}),
 ('Dawit', 'Addis Ababa', 'Ethiopia', 'af', (7, 10), 'dark', {}), ('Joseph', 'Kampala', 'Uganda', 'af', (9, 11), 'dark', {'old': True}),
 ('Ibrahim', 'Bamako', 'Mali', 'af', (10, 11), 'dark', {'hair': 'kufi'}), ('Youssef', 'Casablanca', 'Morocco', 'af', (3, 7), 'darkbrown', {}),
 ('Eric', 'Kigali', 'Rwanda', 'af', (9, 11), 'dark', {}), ('Tendai', 'Harare', 'Zimbabwe', 'af', (9, 11), 'dark', {}),
 ('Javier', 'Madrid', 'Spain', 'eu', (1, 4), 'brownish', {}), ('Marco', 'Rome', 'Italy', 'eu', (1, 4), 'brownish', {}),
 ('Louis', 'Paris', 'France', 'eu', (0, 3), 'any', {}), ('Lukas', 'Berlin', 'Germany', 'eu', (0, 2), 'light', {}),
 ('Erik', 'Oslo', 'Norway', 'eu', (0, 1), 'light', {}), ('Cian', 'Dublin', 'Ireland', 'eu', (0, 1), 'red', {}),
 ('Oliver', 'London', 'UK', 'eu', (0, 11), 'any', {}), ('Tiago', 'Lisbon', 'Portugal', 'eu', (1, 4), 'brownish', {}),
 ('Jakub', 'Warsaw', 'Poland', 'eu', (0, 2), 'light', {}), ('Nikos', 'Athens', 'Greece', 'eu', (1, 4), 'brownish', {'old': True}),
 ('Daan', 'Amsterdam', 'Netherlands', 'eu', (0, 2), 'light', {}), ('Lars', 'Stockholm', 'Sweden', 'eu', (0, 1), 'light', {}),
 ('Mikko', 'Helsinki', 'Finland', 'eu', (0, 1), 'light', {}), ('Dmytro', 'Kyiv', 'Ukraine', 'eu', (0, 2), 'any', {}),
 ('Bence', 'Budapest', 'Hungary', 'eu', (0, 3), 'any', {}), ('Callum', 'Edinburgh', 'Scotland', 'eu', (0, 1), 'red', {}),
 ('Michael', 'New York', 'USA', 'am', (0, 11), 'any', {}), ('Marcus', 'Atlanta', 'USA', 'am', (8, 11), 'darkdye', {}),
 ('Ethan', 'Los Angeles', 'USA', 'am', (0, 6), 'any', {}), ('Takoda', 'Phoenix', 'USA', 'am', (5, 8), 'dark', {}),
 ('Diego', 'Mexico City', 'Mexico', 'am', (3, 7), 'brownish', {}), ('Santiago', 'Bogotá', 'Colombia', 'am', (2, 7), 'brownish', {}),
 ('Mateo', 'Buenos Aires', 'Argentina', 'am', (1, 4), 'any', {}), ('Lucas', 'São Paulo', 'Brazil', 'am', (2, 9), 'any', {}),
 ('Rafael', 'Rio de Janeiro', 'Brazil', 'am', (6, 10), 'brownish', {}), ('Andrés', 'Lima', 'Peru', 'am', (4, 8), 'dark', {}),
 ('Benjamín', 'Santiago', 'Chile', 'am', (1, 5), 'any', {}), ('Andre', 'Kingston', 'Jamaica', 'am', (9, 11), 'dark', {'hair': 'locs'}),
 ('Ernesto', 'Havana', 'Cuba', 'am', (4, 9), 'brownish', {'old': True}), ('Liam', 'Toronto', 'Canada', 'am', (0, 11), 'any', {}),
 ('Noah', 'Vancouver', 'Canada', 'am', (0, 3), 'any', {}), ('Darnell', 'Chicago', 'USA', 'am', (8, 11), 'darkdye', {}),
 ('Joaquín', 'Oaxaca', 'Mexico', 'am', (5, 8), 'dark', {}), ('Carlos', 'Quito', 'Ecuador', 'am', (4, 8), 'dark', {}),
 ('Jack', 'Sydney', 'Australia', 'oc', (0, 3), 'any', {}), ('Harrison', 'Melbourne', 'Australia', 'oc', (0, 2), 'light', {}),
 ('Tama', 'Auckland', 'New Zealand', 'oc', (5, 9), 'dark', {}), ('Kai', 'Honolulu', 'USA', 'oc', (4, 8), 'dark', {}),
 ('Jone', 'Suva', 'Fiji', 'oc', (8, 11), 'dark', {}), ('Sione', "Nuku'alofa", 'Tonga', 'oc', (7, 10), 'dark', {}),
]
assert len(MEN) == 100, len(MEN)
MEN_HAIR = ['santosh', 'crop', 'buzz', 'sidepart_m', 'quiff', 'slick', 'curly_top', 'messy', 'manbun', 'long_m', 'cap', 'beanie']
MEN_CURLY = ['afro_m', 'hightop', 'locs', 'cornrows', 'curly_top', 'buzz']
MEN_TOPS = ['puffer', 'hoodie', 'track', 'blazer', 'sweater', 'denim', 'shirt', 'polo']
BEARDS = ['none', 'none', 'none', 'stubble', 'short', 'full', 'goatee', 'chinstrap']
CAPC = ['#1e88e5', '#212121', '#b71c1c', '#2e7d32', '#ffb300', '#6a1b9a', '#00838f', '#f4511e']


def make_m(rng, i, person):
    name, city, country, region, (s0, s1), pool, sp = person
    skin = rng.randint(s0, s1)
    old = sp.get('old')
    hs = sp.get('hair')
    if not hs:
        opts = list(MEN_HAIR)
        if region == 'af' or (region == 'am' and skin >= 8): opts += MEN_CURLY * 2
        if old: opts = ['bald', 'bald', 'crop', 'sidepart_m', 'slick', 'buzz']
        hs = rng.choice(opts)
    look_hair = {'style': hs}
    real = HAIR['silver'] if old else HAIR[rng.choice(POOLS[pool])]
    if hs == 'dastar': look_hair['color'] = rng.choice(['#ef6c00', '#1565c0', '#212121', '#ad1457', '#f9a825', '#00695c', '#ffffff'])
    elif hs == 'kufi': look_hair['color'] = rng.choice(['#f4f1ea', '#212121', '#6a1b9a', '#c62828', '#1565c0'])
    elif hs == 'ghutra': look_hair.update(color=real, wear=rng.choice(['#f7f5f0', '#f7f5f0', '#c62828']))
    elif hs in ('cap', 'beanie'): look_hair.update(color=real, wear=rng.choice(CAPC))
    else: look_hair['color'] = real
    if hs not in ('dastar', 'kufi', 'ghutra', 'cap', 'beanie', 'bald', 'buzz'): look_hair['part'] = rng.choice(['c', 'l', 'r'])
    top = sp.get('top') or rng.choice(MEN_TOPS + (['kurta'] if region == 'sa' else []))
    if hs == 'ghutra' and not sp.get('top'): top = 'thobe'
    tc, tc2 = rng.sample(COL, 2)
    if top == 'thobe':
        tc, tc2 = '#fbfaf6', '#d9d3c8'
        bottom = {'style': 'long', 'color': '#fbfaf6', 'color2': '#fbfaf6'}
    elif top == 'kurta':
        tc = rng.choice(['#f4f1ea', '#ffd54f', '#e8f5e9', '#90caf9', '#ffffff', '#f8bbd0', '#c5e1a5', '#d7ccc8'])
        bottom = {'style': 'pants', 'color': rng.choice(['#f4f1ea', '#ffffff', '#212121', tc2])}
    else:
        bs = rng.choice(['pants', 'jeans', 'jeans', 'pants', 'shorts'] if not old else ['pants', 'pants'])
        bottom = {'style': bs, 'color': rng.choice(['#3b5b8c', '#24477a', '#2c3566']) if bs == 'jeans' else rng.choice(['#2a2a33', '#37474f', '#3e2723', '#455a64', '#f2e3c9', '#795548', '#212121'] + COL[:6])}
    beard = sp.get('beard') or (rng.choice(['full', 'short', 'none']) if old else rng.choice(BEARDS))
    if hs == 'long_m' and beard == 'none': beard = rng.choice(['short', 'full', 'stubble'])
    if hs == 'long_m' and beard in ('stubble', 'goatee', 'chinstrap'): beard = 'short'      # long hair always with a real beard
    mustache = sp.get('mustache') or ('none' if beard in ('full',) else rng.choice(['none', 'none', 'classic', 'classic', 'thick'] + (['handlebar'] if region == 'sa' else [])))
    acc = []
    if region == 'sa' and rng.random() < .2: acc.append('tilak')
    if rng.random() < .3: acc.append('watch')
    if rng.random() < .12: acc.append('studs')
    if top in ('sweater', 'blazer', 'denim', 'puffer') and rng.random() < .15: acc.append('scarf')
    if rng.random() < .15: acc.append('sling')
    if hs == 'beanie' and rng.random() < .5: acc.append('pom')
    if skin <= 2 and pool in ('red', 'light', 'any') and rng.random() < .3: acc.append('freckles')
    acc = sorted(set(acc))
    glasses = {'style': 'none'}
    if old or rng.random() < .4:
        g = rng.choice(['round', 'square', 'square', 'thin', 'big'] + (['thin', 'round'] if old else []))
        glasses = {'style': g, 'color': '#c9a24a' if g == 'thin' else rng.choice(['#141416', '#141416', '#5a2d1a', '#1e88e5', '#8d6e63', '#c9a24a', '#455a64'])}
    look = {
        'id': 'm%03d' % (i + 1), 'name': name, 'city': city, 'country': country, 'region': region, 'gender': 'm',
        'skin': SKIN[skin], 'eyes': EYES[rng.choice(['darkbrown', 'brown', 'brown', 'hazel', 'amber'] + (['green', 'blue', 'grey', 'blue'] if pool in ('light', 'red') else ['green'] if pool in ('any', 'brownish') else []))],
        'lips': rng.choice(['#8c4a3a', '#7c3020', '#9c4a3e', '#a0524a', '#6e2a24', '#b0625a']), 'hair': look_hair,
        'beard': beard, 'mustache': mustache, 'beardColor': real, 'glasses': glasses,
        'top': {'style': top, 'color': tc, 'color2': tc2}, 'bottom': bottom,
        'shoes': rng.choice(['#f7f5f2', '#f7f5f2', '#212121', '#3e2723', '#90caf9', '#a1887f', '#ffffff', '#ffb300']),
        'laces': rng.choice(COL), 'phone': rng.choice(['#26272c', '#26272c', '#26272c', '#90a4ae', '#80cbc4', '#ffcc80', '#455a64']),
        'acc': acc, 'accColor': rng.choice(['#c62828', '#1565c0', '#2e7d32', '#6a1b9a', '#ff6f00', '#00838f']),
    }
    if top == 'kurta' and rng.random() < .55: look['top']['vest'] = rng.choice(['#2f3b52', '#3e2723', '#004d40', '#4a148c', '#b71c1c', '#d9a441'])
    if top == 'puffer' and rng.random() < .5 or rng.random() < .1: look['straps'] = rng.choice(['#27358c', '#212121', '#ff7043', '#00897b', '#f9a825'])
    if old: look['scale'] = .95; look['old'] = True
    else: look['scale'] = round(rng.uniform(.98, 1.03), 3)
    return look


def feats_m(l):
    return feats(l) + [l['beard'], l['mustache'], l['hair'].get('wear')]


def diff_m(a, b): return sum(x != y for x, y in zip(feats_m(a), feats_m(b)))

def main():
    rng = random.Random(20261020)
    looks = []
    for i, p in enumerate(PEOPLE):
        for attempt in range(400):
            l = make(rng, i, p)
            if all(diff(l, o) >= MIN_DIFF and (l['hair']['style'], l['hair']['color'], l['top']['style']) != (o['hair']['style'], o['hair']['color'], o['top']['style']) for o in looks):
                break
        else: raise SystemExit('could not make %s unique' % p[0])
        looks.append(l)
    worst = min(diff(a, b) for a, b in itertools.combinations(looks, 2))
    rng_m = random.Random(20261020 + 1)
    men = []
    for i, p in enumerate(MEN):
        for attempt in range(400):
            l = make_m(rng_m, i, p)
            if all(diff_m(l, o) >= MIN_DIFF and (l['hair']['style'], l['hair']['color'], l['top']['style'], l['beard']) != (o['hair']['style'], o['hair']['color'], o['top']['style'], o['beard']) for o in men):
                break
        else: raise SystemExit('could not make %s unique' % p[0])
        men.append(l)
    worst_m = min(diff_m(a, b) for a, b in itertools.combinations(men, 2))
    looks = looks + men
    js = '/* generated by tool/avatars/gen_looks.py - 100 female + 100 male Hoola looks */\nwindow.HOOLA_LOOKS = ' + json.dumps(looks, ensure_ascii=False, separators=(',', ':')) + ';\n'
    open(os.path.join(ROOT, 'assets/santosh3d/looks.js'), 'w', encoding='utf8').write(js)
    slim = [{k: l[k] for k in ('id', 'name', 'city', 'country', 'region', 'gender')} | {'hair': l['hair']['style'], 'outfit': l['top']['style']} for l in looks]
    os.makedirs(os.path.join(ROOT, 'server/app/avatar'), exist_ok=True)
    json.dump(slim, open(os.path.join(ROOT, 'server/app/avatar/looks.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    json.dump(looks, open(os.path.join(ROOT, 'tool/avatars/looks_full.json'), 'w', encoding='utf8'), ensure_ascii=False)
    from collections import Counter
    print('looks', len(looks), 'min pairwise difference women', worst, 'of', len(feats(looks[0])), '| men', worst_m, 'of', len(feats_m(men[0])))
    print('men hair', dict(Counter(l['hair']['style'] for l in men)), '\nmen tops', dict(Counter(l['top']['style'] for l in men)), '\nbeards', dict(Counter(l['beard'] for l in men)))
    print('hair', dict(Counter(l['hair']['style'] for l in looks)))
    print('tops', dict(Counter(l['top']['style'] for l in looks)))
    print('skin tones', len(set(l['skin'] for l in looks)), 'hair colours', len(set(l['hair']['color'] for l in looks)), 'glasses', sum(l['glasses']['style'] != 'none' for l in looks))

if __name__ == '__main__': main()
