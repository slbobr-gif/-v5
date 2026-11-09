"""Арт для хийси и сейда в стиле остальных существ: медальон с лучами, тёмный силуэт, светящиеся глаза."""
import re
from pathlib import Path
D = Path(__file__).resolve().parents[2] / 'app' / 'assets' / 'art' / 'creatures'
T = (D / 'kikimora.svg').read_text()
frame_start = T[:T.index('<g transform')]
frame_end = T[T.index('<path d="M-1,-1 121,-1'):]

def grad(i, a, b, c):
    return (f'<linearGradient id="g{i}" x1="0" y1="0" x2="0.2" y2="1"><stop offset="0" stop-color="{a}"/>'
            f'<stop offset="0.6" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>')

def glow(id_, cx, cy, r, col):
    return (f'<radialGradient id="{id_}" cx="{cx}" cy="{cy}" r="{r}" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{col}" stop-opacity="0.55"/><stop offset="0.5" stop-color="{col}" stop-opacity="0.2"/>'
            f'<stop offset="1" stop-color="{col}" stop-opacity="0.00"/></radialGradient>')

def build(name, rays, halo, eye, ring, eyes, shapes):
    defs = ''.join(grad(i + 1, *c) for i, c in enumerate(rays))
    defs += glow('g5', 60, 40, 40, halo)
    defs += f'<linearGradient id="g7" x1="0" y1="0" x2="0.2" y2="1"><stop offset="0" stop-color="{eye[0]}"/><stop offset="1" stop-color="{eye[1]}"/></linearGradient>'
    for k, (x, y, rx, ry) in enumerate(eyes):
        defs += glow(f'e{k}', x, y, 9, halo)
    head = re.sub(r'<defs>.*</defs>', '<defs>' + defs + '</defs>', frame_start, flags=re.S)
    S = 'fill="#04070A" stroke="#070B10" stroke-width="1.4" stroke-linejoin="round"'
    body = ''.join(f'<path d="{d}" {S}/>' if not d.startswith('E') else
                   '<ellipse cx="{}" cy="{}" rx="{}" ry="{}" {}/>'.format(*d[1:].split(','), S) for d in shapes)
    for k, (x, y, rx, ry) in enumerate(eyes):
        body += (f'<circle cx="{x}" cy="{y}" r="9" fill="url(#e{k})"/>'
                 f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="url(#g7)" stroke="#070B10" stroke-width="0.6"/>')
    tail = frame_end.replace('stroke="#CEB1FF"', f'stroke="{ring}"')
    svg = head + body + tail
    (D / f'{name}.svg').write_text(svg)
    print(name, len(svg))

# Хийси: каменный хозяин сельги, гранитные тона, янтарные глаза
build('hiisi',
      rays=[('#6E5A5E', '#3A2B30', '#30242A'), ('#7D6A6A', '#4A3638', '#3E2D30'),
            ('#5A4A50', '#2E2228', '#261C21'), ('#8C7470', '#5C4440', '#4C3835')],
      halo='#F2C98A', eye=('#FFE2B0', '#E0A860'), ring='#E8C7A8',
      eyes=[(54, 52, 2.6, 1.1), (66, 52, 2.6, 1.1)],
      shapes=[
          'M14,98 L19,82 L16,83 L21,68 L18,69 L23,54 L28,69 L25,68 L30,83 L27,82 L32,98Z',
          'M96,100 L100,86 L98,87 L102,74 L106,87 L104,86 L108,100Z',
          'M8,121 L10,104 C22,94 40,90 60,92 C80,90 98,94 112,104 L114,121Z',
          'M33,104 L36,80 L44,71 L52,68 L68,68 L76,71 L84,80 L87,104Z',
          'M47,70 L45,54 L47,42 L54,35 L64,34 L71,39 L74,50 L72,62 L67,70Z',
          'M36,84 L30,98 L36,100 L42,90Z', 'M84,84 L90,98 L84,100 L78,90Z',
      ])

# Сейд: валун на трёх камнях на вершине сопки, северные зелёные тона
build('seid',
      rays=[('#2F5A55', '#0F2F33', '#0C272B'), ('#3D7A66', '#1A4A40', '#153D35'),
            ('#283E50', '#0E2030', '#0B1A28'), ('#4F8C78', '#2A6050', '#225042')],
      halo='#9FF2C8', eye=('#D8FFEA', '#86D9B0'), ring='#A8F0D0',
      eyes=[(51, 56, 2.4, 0.9), (69, 56, 2.4, 0.9)],
      shapes=[
          'M-1,121 L-1,104 C18,96 38,88 60,88 C82,88 102,96 121,104 L121,121Z',
          'E46,80,4.5,4.6', 'E60,81,4.2,4.6', 'E74,80,4.5,4.6',
          'M28,71 C23,58 31,42 47,37 C60,32 79,34 88,44 C97,53 95,67 89,73 C76,77 42,77 28,71Z',
          'M12,96 L14,92 L17,93 L20,90 L22,94Z', 'M100,94 L103,90 L106,92 L108,96Z',
      ])
