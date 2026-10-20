"""Build the one-file Hoola Moves preview page (the page shown to the owner on 20 Oct 2026).

    python3 tool/moves/build_demo.py   ->  tool/moves/demo.html (open in a browser; three.js r149 from jsDelivr)
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..', '..', 'assets', 'santosh3d')
s = open(os.path.join(HERE, 'demo_template.html'), encoding='utf-8').read()
for key, f in (('AVATAR', 'avatar.js'), ('MOVES', 'moves.js'), ('LOOKS', 'looks.js')):
    s = s.replace('<script>/*%s*/</script>' % key, '<script>\n' + open(os.path.join(R, f), encoding='utf-8').read() + '\n</script>')
open(os.path.join(HERE, 'demo.html'), 'w', encoding='utf-8').write(s)
print('wrote tool/moves/demo.html', len(s) // 1024, 'KB')
