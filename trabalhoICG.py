"""
1º Trabalho - ICG: Cena 3D Interativa em OpenGL
Tema: Cemitério Assombrado

Objetos: chão gramado, túmulos (base + lápide arredondada + cruz),
         árvores secas, lua com halo, fantasma flutuante interativo,
         névoa rastejante, estrelas.

Requisitos atendidos:
  - GLFW + loop de renderização + glClear
  - Double Buffering (glfw.swap_buffers)
  - Objetos distintos modelados via glVertex (GL_QUADS, GL_TRIANGLES, GL_QUAD_STRIP, GL_LINES)
  - Interpolação de cores nos vértices (degradê em todos os objetos)
  - Translação, rotação e escala com valores reais demonstrados
  - Composição de transformações (fantasma: pos. usuário + flutuação + balanço)
  - gluPerspective + gluLookAt + glViewport
  - Teclado: mover câmera e mover objeto (fantasma)

Controles:
  W/S        - câmera frente/trás
  A/D        - câmera esquerda/direita
  Q/E        - câmera cima/baixo
  Setas ←→   - girar câmera
  Setas ↑↓   - inclinar câmera
  I/K        - mover fantasma frente/trás
  J/L        - mover fantasma esquerda/direita
  U/O        - mover fantasma cima/baixo
  P          - pausar/retomar
  R          - resetar câmera e fantasma
  ESC        - sair
"""

import sys, math, random

try:
    import glfw
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "glfw",
                           "--break-system-packages", "-q"])
    import glfw

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "PyOpenGL", "PyOpenGL_accelerate",
                           "--break-system-packages", "-q"])
    from OpenGL.GL import *
    from OpenGL.GLU import *

# ═══════════════════════════════════════════════
# Paleta de cores (tema noturno azul-roxo)
# ═══════════════════════════════════════════════
SKY_TOP    = (0.04, 0.03, 0.10)
SKY_MID    = (0.06, 0.05, 0.16)
GROUND_FAR = (0.05, 0.09, 0.06)
GROUND_MID = (0.08, 0.13, 0.08)
GROUND_NEAR= (0.11, 0.17, 0.10)
STONE_TOP  = (0.62, 0.64, 0.70)
STONE_BOT  = (0.28, 0.30, 0.36)
WOOD_DARK  = (0.18, 0.13, 0.09)
WOOD_LIGHT = (0.30, 0.22, 0.14)
GHOST_CTR  = (0.82, 0.95, 0.88)
GHOST_EDGE = (0.38, 0.60, 0.52)
FOG_COLOR  = (0.40, 0.60, 0.50, 0.22)

# ═══════════════════════════════════════════════
# Estado global
# ═══════════════════════════════════════════════
WINDOW_W, WINDOW_H = 1024, 768

cam = {"x": 0.0, "y": 2.8, "z": 13.5, "yaw": 0.0, "pitch": -9.0}
ghost_pos = {"x": -0.5, "y": 2.2, "z": 1.5}

anim = {
    "paused": False,
    "time":        0.0,
    "ghost_float": 0.0,
    "ghost_sway":  0.0,
    "moon_pulse":  0.0,
    # Mãos de zumbi: phase = "idle" | "rising" | "holding" | "sinking"
    "zombie_phase":    "idle",
    "zombie_progress": 0.0,   # 0.0 = sob o chão, 1.0 = totalmente visível
}

keys_pressed = set()

_rng = random.Random(99)
_STARS = [(_rng.uniform(-50,50), _rng.uniform(4,40),
           _rng.uniform(-55,-4),  _rng.uniform(0.35, 1.0))
          for _ in range(220)]

# ═══════════════════════════════════════════════
# Callbacks
# ═══════════════════════════════════════════════
def key_callback(window, key, scancode, action, mods):
    if action == glfw.PRESS:
        keys_pressed.add(key)
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        if key == glfw.KEY_P:
            anim["paused"] = not anim["paused"]
        if key == glfw.KEY_M:
            # Só dispara se estiver idle (evita re-trigger durante animação)
            if anim["zombie_phase"] == "idle":
                anim["zombie_phase"]    = "rising"
                anim["zombie_progress"] = 0.0
        if key == glfw.KEY_R:
            cam.update({"x":0.0,"y":2.8,"z":13.5,"yaw":0.0,"pitch":-9.0})
            ghost_pos.update({"x":-0.5,"y":2.2,"z":1.5})
    elif action == glfw.RELEASE:
        keys_pressed.discard(key)


def process_keys():
    ms, os_, rs = 0.10, 0.08, 1.1
    yr = math.radians(cam["yaw"])
    fx, fz = math.sin(yr), -math.cos(yr)
    if glfw.KEY_W in keys_pressed: cam["x"]+=fx*ms; cam["z"]+=fz*ms
    if glfw.KEY_S in keys_pressed: cam["x"]-=fx*ms; cam["z"]-=fz*ms
    if glfw.KEY_A in keys_pressed: cam["x"]-=fz*ms; cam["z"]+=fx*ms
    if glfw.KEY_D in keys_pressed: cam["x"]+=fz*ms; cam["z"]-=fx*ms
    if glfw.KEY_Q in keys_pressed: cam["y"]+=ms
    if glfw.KEY_E in keys_pressed: cam["y"]-=ms
    if glfw.KEY_LEFT  in keys_pressed: cam["yaw"]-=rs
    if glfw.KEY_RIGHT in keys_pressed: cam["yaw"]+=rs
    if glfw.KEY_UP    in keys_pressed: cam["pitch"]=min(cam["pitch"]+rs, 89)
    if glfw.KEY_DOWN  in keys_pressed: cam["pitch"]=max(cam["pitch"]-rs,-89)
    if glfw.KEY_I in keys_pressed: ghost_pos["z"]-=os_
    if glfw.KEY_K in keys_pressed: ghost_pos["z"]+=os_
    if glfw.KEY_J in keys_pressed: ghost_pos["x"]-=os_
    if glfw.KEY_L in keys_pressed: ghost_pos["x"]+=os_
    if glfw.KEY_U in keys_pressed: ghost_pos["y"]+=os_
    if glfw.KEY_O in keys_pressed: ghost_pos["y"]-=os_


def framebuffer_size_callback(window, w, h):
    if h == 0: h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(48.0, w/h, 0.1, 200.0)
    glMatrixMode(GL_MODELVIEW)


# ═══════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════
def c3(rgb):  glColor3f(*rgb)
def c4(rgba): glColor4f(*rgba)
def lerp(a, b, t): return a + (b-a)*t
def lerpRGB(ca, cb, t):
    return (lerp(ca[0],cb[0],t), lerp(ca[1],cb[1],t), lerp(ca[2],cb[2],t))


# ═══════════════════════════════════════════════
# Céu gradiente (ortho 2D)
# ═══════════════════════════════════════════════
def draw_sky_backdrop():
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    glOrtho(-1,1,-1,1,-1,1)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glBegin(GL_QUADS)
    c3(SKY_MID); glVertex2f(-1,-1)
    c3(SKY_MID); glVertex2f( 1,-1)
    c3(SKY_TOP); glVertex2f( 1, 1)
    c3(SKY_TOP); glVertex2f(-1, 1)
    glEnd()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()
    glEnable(GL_DEPTH_TEST)


# ═══════════════════════════════════════════════
# Chão
# ═══════════════════════════════════════════════
def draw_ground():
    hs = 22.0
    steps = 14
    for i in range(steps):
        z0 = lerp( hs,-hs, i/steps)
        z1 = lerp( hs,-hs,(i+1)/steps)
        c0 = lerpRGB(GROUND_NEAR, GROUND_FAR, i/steps)
        c1 = lerpRGB(GROUND_NEAR, GROUND_FAR,(i+1)/steps)
        glBegin(GL_QUADS)
        c3(c0); glVertex3f(-hs,0,z0)
        c3(c0); glVertex3f( hs,0,z0)
        c3(c1); glVertex3f( hs,0,z1)
        c3(c1); glVertex3f(-hs,0,z1)
        glEnd()


# ═══════════════════════════════════════════════
# Lua com halo
# ═══════════════════════════════════════════════
def draw_moon_with_halo(pt):
    scale = 1.0 + 0.05*math.sin(pt)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Halo externo
    glPushMatrix(); glScalef(scale,scale,1)
    segs=40
    glBegin(GL_TRIANGLE_FAN)
    glColor4f(0.80,0.85,0.60,0.0); glVertex2f(0,0)
    for i in range(segs+1):
        a=2*math.pi*i/segs
        alpha=0.16*abs(math.sin(pt*0.7+i*0.1))
        glColor4f(0.70,0.78,0.50,alpha)
        glVertex2f(math.cos(a)*2.2, math.sin(a)*2.2)
    glEnd()
    glPopMatrix()

    # Disco lunar
    glPushMatrix(); glScalef(scale,scale,1)
    glBegin(GL_TRIANGLE_FAN)
    glColor3f(0.96,0.96,0.82); glVertex2f(0,0)
    for i in range(segs+1):
        a=2*math.pi*i/segs
        t=0.5+0.5*math.sin(a*3)
        c3(lerpRGB((0.72,0.78,0.60),(0.90,0.92,0.76),t))
        glVertex2f(math.cos(a)*1.3, math.sin(a)*1.3)
    glEnd()
    # Crateras
    for (cx,cy,cr) in [(0.3,0.2,0.22),(-0.4,0.4,0.16),(0.1,-0.5,0.13),(-0.2,-0.1,0.10)]:
        glBegin(GL_TRIANGLE_FAN)
        glColor3f(0.72,0.74,0.60); glVertex2f(cx,cy)
        for i in range(12):
            a=2*math.pi*i/12
            glColor3f(0.64,0.66,0.52)
            glVertex2f(cx+math.cos(a)*cr, cy+math.sin(a)*cr)
        glEnd()
    glPopMatrix()
    glDisable(GL_BLEND)


# ═══════════════════════════════════════════════
# Estrelas cintilantes
# ═══════════════════════════════════════════════
def draw_stars(t):
    glPointSize(1.8)
    glBegin(GL_POINTS)
    for i,(sx,sy,sz,b) in enumerate(_STARS):
        tw = b*(0.7+0.3*math.sin(t*1.5+i*0.8))
        glColor3f(tw,tw,tw*0.90)
        glVertex3f(sx,sy,sz)
    glEnd()
    glPointSize(1.0)


# ═══════════════════════════════════════════════
# Mãos de Zumbi  (10 personalidades distintas)
# ═══════════════════════════════════════════════

# Variações de cor de pele: do verde-musgo ao cinza-putrefato
_HAND_SKINS = [
    ((0.26, 0.40, 0.16), (0.13, 0.22, 0.08), (0.07, 0.11, 0.04)),  # 0 verde intenso
    ((0.32, 0.36, 0.20), (0.16, 0.20, 0.10), (0.06, 0.10, 0.03)),  # 1 verde-oliva
    ((0.22, 0.30, 0.18), (0.10, 0.18, 0.08), (0.05, 0.08, 0.03)),  # 2 verde escuro
    ((0.38, 0.34, 0.22), (0.20, 0.18, 0.11), (0.09, 0.08, 0.04)),  # 3 verde-amarelado
    ((0.28, 0.32, 0.24), (0.15, 0.18, 0.12), (0.06, 0.07, 0.04)),  # 4 cinza-esverdeado
    ((0.24, 0.28, 0.20), (0.12, 0.15, 0.09), (0.05, 0.06, 0.03)),  # 5 verde-acinzentado
    ((0.30, 0.42, 0.14), (0.14, 0.24, 0.06), (0.08, 0.12, 0.02)),  # 6 verde-vivo
    ((0.20, 0.26, 0.22), (0.09, 0.14, 0.11), (0.04, 0.06, 0.04)),  # 7 cinza-esverdeado escuro
    ((0.35, 0.38, 0.18), (0.18, 0.20, 0.08), (0.10, 0.10, 0.03)),  # 8 verde-marrom
    ((0.27, 0.35, 0.21), (0.13, 0.19, 0.10), (0.06, 0.09, 0.04)),  # 9 verde-médio
]

def _cylinder(r0, r1, h, segs, col_bot, col_top):
    """Cilindro/tronco de cone vertical simples."""
    glBegin(GL_QUAD_STRIP)
    for i in range(segs + 1):
        a = 2 * math.pi * i / segs
        ca, sa = math.cos(a), math.sin(a)
        c3(col_bot); glVertex3f(ca*r0, 0, sa*r0)
        c3(col_top); glVertex3f(ca*r1, h, sa*r1)
    glEnd()

def _draw_finger_segment(r0, r1, length, segs, skin, dark):
    """Um segmento de dedo: cone + articulação esférica."""
    _cylinder(r0, r1, length, segs, dark, skin)
    # articulação esférica no topo
    glPushMatrix()
    glTranslatef(0, length, 0)
    nr = (r0+r1)*0.55
    glBegin(GL_TRIANGLE_FAN)
    c3(lerpRGB(dark, skin, 0.6)); glVertex3f(0, 0, 0)
    for i in range(segs+1):
        a = 2*math.pi*i/segs
        c3(dark); glVertex3f(math.cos(a)*nr, 0, math.sin(a)*nr)
    glEnd()
    glPopMatrix()

def _draw_nail(length, width, skin, nail_col):
    """Garra/unha pontiaguda e curvada."""
    w, h = width, length
    glBegin(GL_TRIANGLES)
    c3(nail_col)
    glVertex3f(-w,  0,    0.015)
    glVertex3f( w,  0,    0.015)
    c3(lerpRGB(nail_col, (0,0,0), 0.5))
    glVertex3f( 0,  h,   -0.010)
    # face lateral esquerda
    c3(nail_col)
    glVertex3f(-w,  0,    0.015)
    c3(lerpRGB(nail_col, (0,0,0), 0.5))
    glVertex3f( 0,  h,   -0.010)
    glVertex3f( 0,  0,   -0.010)
    # face lateral direita
    c3(nail_col)
    glVertex3f( w,  0,    0.015)
    glVertex3f( 0,  0,   -0.010)
    c3(lerpRGB(nail_col, (0,0,0), 0.5))
    glVertex3f( 0,  h,   -0.010)
    glEnd()

def _draw_dirt_clump(seed):
    """Torrão de terra na base, variado por seed."""
    rng = random.Random(seed)
    DIRT  = (0.18, 0.12, 0.07)
    DIRT2 = (0.26, 0.18, 0.10)
    glBegin(GL_TRIANGLES)
    for _ in range(10):
        angle = rng.uniform(0, 2*math.pi)
        r1    = rng.uniform(0.08, 0.20)
        r2    = rng.uniform(0.04, 0.14)
        h     = rng.uniform(0.02, 0.08)
        bx, bz = math.cos(angle)*r1*0.5, math.sin(angle)*r1*0.5
        c3(DIRT)
        glVertex3f(bx - r2*0.5, 0, bz - r2*0.5)
        glVertex3f(bx + r2*0.5, 0, bz + r2*0.5)
        c3(DIRT2)
        glVertex3f(bx, h, bz)
    glEnd()
    # cascalho/galhos
    glLineWidth(1.5)
    glBegin(GL_LINES)
    for _ in range(5):
        angle = rng.uniform(0, 2*math.pi)
        r = rng.uniform(0.06, 0.16)
        c3(lerpRGB(DIRT, (0.08,0.06,0.04), 0.5))
        glVertex3f(0, rng.uniform(0,0.04), 0)
        c3((0.10, 0.07, 0.04))
        glVertex3f(math.cos(angle)*r, 0.01, math.sin(angle)*r)
    glEnd()
    glLineWidth(1.0)

# Definições das 10 mãos individuais
# Cada entrada: (arm_r, palm_w, palm_h, fingers, wobble_speed, wobble_amp)
# fingers: lista de (offset_x, offset_z, length, spread_deg, curl_deg, thickness, is_thumb)
_HAND_DEFS = [
    # 0: mão espalmada, dedos abertos apontando pra cima – clássica saindo do túmulo
    dict(arm_r=0.075, palm_w=0.14, palm_h=0.26, wsp=1.2, wamp=3.0,
         fingers=[
             (-0.11, 0.0, 0.30, -18,  5, 0.030, False),
             (-0.05, 0.0, 0.34,  -6,  3, 0.033, False),
             ( 0.01, 0.0, 0.36,   3,  2, 0.034, False),
             ( 0.07, 0.0, 0.32,  13,  4, 0.031, False),
             ( 0.13, 0.06,0.22,  32,  8, 0.026, True ),
         ]),
    # 1: mão crispada, dedos dobrados como garra, mais fina
    dict(arm_r=0.065, palm_w=0.12, palm_h=0.22, wsp=1.8, wamp=5.0,
         fingers=[
             (-0.10, 0.0, 0.28, -16, 55, 0.028, False),
             (-0.04, 0.0, 0.31,  -5, 50, 0.030, False),
             ( 0.02, 0.0, 0.33,   4, 45, 0.031, False),
             ( 0.08, 0.0, 0.30,  14, 50, 0.029, False),
             ( 0.12, 0.07,0.20,  30, 35, 0.024, True ),
         ]),
    # 2: mão grande e larga, dedos grossos meio abertos
    dict(arm_r=0.090, palm_w=0.17, palm_h=0.28, wsp=0.9, wamp=2.0,
         fingers=[
             (-0.13, 0.0, 0.26, -20, 15, 0.038, False),
             (-0.06, 0.0, 0.30,  -7, 10, 0.040, False),
             ( 0.01, 0.0, 0.32,   2, 10, 0.042, False),
             ( 0.08, 0.0, 0.29,  12, 12, 0.039, False),
             ( 0.14, 0.07,0.21,  30, 18, 0.033, True ),
         ]),
    # 3: mão pequena e ossuda, dedos longos e finos muito dobrados
    dict(arm_r=0.058, palm_w=0.10, palm_h=0.20, wsp=2.2, wamp=6.0,
         fingers=[
             (-0.09, 0.0, 0.36, -14, 70, 0.022, False),
             (-0.03, 0.0, 0.40,  -4, 65, 0.024, False),
             ( 0.02, 0.0, 0.42,   5, 60, 0.025, False),
             ( 0.07, 0.0, 0.38,  15, 65, 0.023, False),
             ( 0.11, 0.06,0.24,  28, 40, 0.020, True ),
         ]),
    # 4: mão inclinada lateral, 3 dedos eretos 2 curvados (dedo perdido)
    dict(arm_r=0.070, palm_w=0.13, palm_h=0.23, wsp=1.5, wamp=4.0,
         fingers=[
             (-0.10, 0.0, 0.29, -17, 80, 0.027, False),  # mindinho curvado
             (-0.04, 0.0, 0.32,  -6, 75, 0.029, False),  # anelar curvado
             ( 0.02, 0.0, 0.34,   3,  8, 0.031, False),  # médio ereto
             ( 0.08, 0.0, 0.31,  13,  6, 0.029, False),  # indicador ereto
             ( 0.12, 0.07,0.21,  29, 12, 0.024, True ),  # polegar
         ]),
    # 5: mão larga e achatada, espalmada com dedos bem separados
    dict(arm_r=0.082, palm_w=0.16, palm_h=0.25, wsp=1.0, wamp=2.5,
         fingers=[
             (-0.14, 0.0, 0.27, -26,  8, 0.032, False),
             (-0.06, 0.0, 0.31,  -8,  5, 0.035, False),
             ( 0.01, 0.0, 0.33,   3,  4, 0.036, False),
             ( 0.09, 0.0, 0.30,  15,  6, 0.033, False),
             ( 0.16, 0.06,0.22,  38,  9, 0.028, True ),
         ]),
    # 6: mão velha e nodosa, dedos retorcidos com ângulos irregulares
    dict(arm_r=0.068, palm_w=0.12, palm_h=0.21, wsp=2.0, wamp=3.5,
         fingers=[
             (-0.10, 0.0, 0.28, -19, 30, 0.026, False),
             (-0.04, 0.0, 0.31,  -3, 20, 0.028, False),
             ( 0.02, 0.0, 0.33,   8, 40, 0.029, False),
             ( 0.08, 0.0, 0.30,  17, 15, 0.027, False),
             ( 0.12, 0.07,0.20,  31, 22, 0.022, True ),
         ]),
    # 7: punho semi-fechado, quase soqueando
    dict(arm_r=0.078, palm_w=0.14, palm_h=0.24, wsp=1.6, wamp=2.0,
         fingers=[
             (-0.10, 0.0, 0.26, -15, 85, 0.030, False),
             (-0.04, 0.0, 0.30,  -4, 82, 0.032, False),
             ( 0.02, 0.0, 0.32,   5, 80, 0.033, False),
             ( 0.08, 0.0, 0.29,  14, 82, 0.031, False),
             ( 0.10, 0.08,0.21,  20, 55, 0.026, True ),
         ]),
    # 8: mão grande pedindo socorro – dedos todos esticados, bem abertos
    dict(arm_r=0.085, palm_w=0.15, palm_h=0.27, wsp=0.8, wamp=4.5,
         fingers=[
             (-0.12, 0.0, 0.31, -22,  2, 0.035, False),
             (-0.05, 0.0, 0.35,  -7,  1, 0.037, False),
             ( 0.01, 0.0, 0.37,   2,  1, 0.038, False),
             ( 0.08, 0.0, 0.34,  12,  2, 0.036, False),
             ( 0.15, 0.06,0.24,  35,  3, 0.030, True ),
         ]),
    # 9: mão fina só com 3 dedos funcionais (2 dobrados como decepados)
    dict(arm_r=0.062, palm_w=0.11, palm_h=0.21, wsp=1.9, wamp=5.5,
         fingers=[
             (-0.09, 0.0, 0.12, -16, 88, 0.024, False),  # "decepado"
             (-0.03, 0.0, 0.13,  -4, 88, 0.026, False),  # "decepado"
             ( 0.02, 0.0, 0.34,   4,  5, 0.028, False),
             ( 0.07, 0.0, 0.32,  13,  8, 0.027, False),
             ( 0.11, 0.07,0.22,  27, 18, 0.022, True ),
         ]),
]

def draw_zombie_hand(t, hand_id=0):
    """Desenha a mão de zumbi #hand_id (0-9). Origem y=0 = nível do chão."""
    hd   = _HAND_DEFS[hand_id % len(_HAND_DEFS)]
    skin_col, dark_col, nail_col = _HAND_SKINS[hand_id % len(_HAND_SKINS)]
    segs = 9

    arm_r  = hd["arm_r"]
    pw, ph = hd["palm_w"], hd["palm_h"]
    wsp, wamp = hd["wsp"], hd["wamp"]

    # ── Torrão de terra na base ──
    _draw_dirt_clump(hand_id * 13 + 7)

    # ── Antebraço emergindo ──
    arm_h = 0.60
    _cylinder(arm_r * 0.85, arm_r, arm_h, segs, dark_col, skin_col)
    # veias no antebraço (linhas escuras)
    glLineWidth(1.2)
    glBegin(GL_LINES)
    for vi in range(3):
        a = 2*math.pi*vi/3
        vx, vz = math.cos(a)*arm_r*0.92, math.sin(a)*arm_r*0.92
        c3(dark_col)
        glVertex3f(vx, 0.10, vz)
        c3(lerpRGB(dark_col, skin_col, 0.4))
        glVertex3f(vx*0.95, arm_h, vz*0.95)
    glEnd()
    glLineWidth(1.0)

    # ── Pulso (engrossamento) ──
    glPushMatrix()
    glTranslatef(0, arm_h, 0)
    _cylinder(arm_r, arm_r*1.20, 0.08, segs, skin_col, skin_col)

    # ── Palma achatada ──
    glTranslatef(0, 0.08, 0)
    glPushMatrix()
    glScalef(1.0, 1.0, 0.70)       # achatada no eixo Z
    _cylinder(arm_r*1.15, pw, ph, segs, lerpRGB(dark_col,skin_col,0.5), skin_col)
    # tampa da palma
    glPushMatrix()
    glTranslatef(0, ph, 0)
    glBegin(GL_TRIANGLE_FAN)
    c3(skin_col); glVertex3f(0,0,0)
    for i in range(segs+1):
        a=2*math.pi*i/segs; c3(dark_col)
        glVertex3f(math.cos(a)*pw, 0, math.sin(a)*pw)
    glEnd()
    glPopMatrix()
    glPopMatrix()   # /escala palma

    palm_top = ph

    # ── Dedos ──
    wobble = wamp * math.sin(t * wsp)

    for fi, (fx, fz, flen, spread, curl, frad, is_thumb) in enumerate(hd["fingers"]):
        glPushMatrix()
        glTranslatef(fx, palm_top, fz)

        # spread lateral (abre/fecha)
        glRotatef(spread + wobble * 0.25, 0, 0, 1)

        if is_thumb:
            glRotatef(-20, 1, 0, 0)   # polegar sai mais horizontal
            glRotatef( 15, 0, 1, 0)
        else:
            glRotatef(-8, 1, 0, 0)    # inclinação natural pra frente

        # ── segmento proximal ──
        seg_h = flen * 0.42
        _draw_finger_segment(frad, frad*0.94, seg_h, segs, skin_col, dark_col)

        glTranslatef(0, seg_h, 0)
        glRotatef(curl * 0.55, 1, 0, 0)   # primeira dobra

        # ── segmento médio ──
        seg_h2 = flen * 0.36
        _draw_finger_segment(frad*0.88, frad*0.78, seg_h2, segs, skin_col, dark_col)

        glTranslatef(0, seg_h2, 0)
        glRotatef(curl * 0.45, 1, 0, 0)   # segunda dobra

        # ── segmento distal ──
        seg_h3 = flen * 0.28
        _draw_finger_segment(frad*0.72, frad*0.56, seg_h3, segs, skin_col, dark_col)

        glTranslatef(0, seg_h3, 0)

        # ── garra / unha ──
        nail_len  = 0.065 if not is_thumb else 0.050
        nail_w    = frad * 0.80
        _draw_nail(nail_len, nail_w, skin_col, nail_col)

        glPopMatrix()

    glPopMatrix()   # /pulso+palma


# ═══════════════════════════════════════════════
# Túmulo
# ═══════════════════════════════════════════════
def draw_grave(sx=1.0, sy=1.0):
    # Montículo de terra
    glBegin(GL_QUADS)
    glColor3f(0.22,0.18,0.12)
    glVertex3f(-0.52,0.00, 0.22); glVertex3f( 0.52,0.00, 0.22)
    glColor3f(0.30,0.24,0.16)
    glVertex3f( 0.42,0.14,-0.30); glVertex3f(-0.42,0.14,-0.30)
    glColor3f(0.30,0.24,0.16)
    glVertex3f(-0.42,0.14,-0.30); glVertex3f( 0.42,0.14,-0.30)
    glColor3f(0.20,0.16,0.10)
    glVertex3f( 0.38,0.06,-0.78); glVertex3f(-0.38,0.06,-0.78)
    # Frente
    glColor3f(0.14,0.11,0.07)
    glVertex3f(-0.52,0.00, 0.22); glVertex3f( 0.52,0.00, 0.22)
    glColor3f(0.20,0.16,0.10)
    glVertex3f( 0.52,0.14, 0.22); glVertex3f(-0.52,0.14, 0.22)
    glEnd()

    # Lápide com escala real
    glPushMatrix()
    glTranslatef(0.0, 0.06, -0.55)
    glScalef(sx, sy, 1.0)          # <<< escala real demonstrada
    W, H = 0.32, 0.88

    # Face frontal
    glBegin(GL_QUADS)
    c3(STONE_TOP); glVertex3f(-W,H, 0.04)
    c3(STONE_TOP); glVertex3f( W,H, 0.04)
    c3(STONE_BOT); glVertex3f( W,0, 0.04)
    c3(STONE_BOT); glVertex3f(-W,0, 0.04)
    glEnd()
    # Laterais
    for (xa,xb) in [(-W,-W),(W,W)]:
        glBegin(GL_QUADS)
        c3(lerpRGB(STONE_BOT,STONE_TOP,0.3))
        glVertex3f(xa,0,0.00); glVertex3f(xb,H,0.00)
        glVertex3f(xb,H,0.04); glVertex3f(xa,0,0.04)
        glEnd()
    # Costas
    glBegin(GL_QUADS)
    c3(STONE_BOT)
    glVertex3f(-W,0,0.00); glVertex3f(W,0,0.00)
    glVertex3f( W,H,0.00); glVertex3f(-W,H,0.00)
    glEnd()

    # Arco no topo
    segs=12
    glBegin(GL_TRIANGLE_FAN)
    c3(lerpRGB(STONE_TOP,(1,1,1),0.15)); glVertex3f(0,H+W,0.04)
    for i in range(segs+1):
        a=math.pi*i/segs
        t=0.5+0.5*math.cos(a)
        c3(lerpRGB(STONE_BOT,STONE_TOP,t))
        glVertex3f(math.cos(a)*W, H+math.sin(a)*W, 0.04)
    glEnd()
    glBegin(GL_TRIANGLE_FAN)
    c3(STONE_BOT); glVertex3f(0,H+W,0.0)
    for i in range(segs+1):
        a=math.pi*i/segs
        glVertex3f(math.cos(a)*W, H+math.sin(a)*W, 0.0)
    glEnd()

    # Cruz em relevo
    cx,cy = 0.0, H*0.52
    aw,ah = 0.055, 0.22
    cc = lerpRGB(STONE_BOT,STONE_TOP,0.72)
    glBegin(GL_QUADS)
    c3(cc)
    glVertex3f(cx-aw,cy-ah,0.06); glVertex3f(cx+aw,cy-ah,0.06)
    glVertex3f(cx+aw,cy+ah,0.06); glVertex3f(cx-aw,cy+ah,0.06)
    glVertex3f(cx-ah*0.7,cy+aw*0.3,0.06); glVertex3f(cx+ah*0.7,cy+aw*0.3,0.06)
    glVertex3f(cx+ah*0.7,cy-aw*0.3,0.06); glVertex3f(cx-ah*0.7,cy-aw*0.3,0.06)
    glEnd()
    glPopMatrix()


# ═══════════════════════════════════════════════
# Árvore seca
# ═══════════════════════════════════════════════
def draw_dead_tree(h=4.0):
    segs=8
    # Tronco cônico
    glBegin(GL_QUAD_STRIP)
    for i in range(segs+1):
        a=2*math.pi*i/segs
        c3(WOOD_DARK);  glVertex3f(math.cos(a)*0.20,0,  math.sin(a)*0.20)
        c3(WOOD_LIGHT); glVertex3f(math.cos(a)*0.06,h,  math.sin(a)*0.06)
    glEnd()
    # Tampa
    glBegin(GL_TRIANGLE_FAN)
    c3(WOOD_LIGHT); glVertex3f(0,h,0)
    for i in range(segs+1):
        a=2*math.pi*i/segs
        glVertex3f(math.cos(a)*0.06,h,math.sin(a)*0.06)
    glEnd()
    # Galhos
    glLineWidth(2.5)
    branches=[
        (h*0.55, 1.6,h*0.80, 0.2),
        (h*0.55,-1.4,h*0.78,-0.1),
        (h*0.70, 1.1,h*0.90, 0.3),
        (h*0.70,-1.0,h*0.88,-0.2),
        (h*0.82, 0.7,h*0.97, 0.1),
    ]
    for (yb,ex,ey,ez) in branches:
        mx,my,mz=ex*0.45,(yb+ey)*0.5,ez*0.4
        glBegin(GL_LINE_STRIP)
        c3(WOOD_LIGHT); glVertex3f(0,yb,0)
        c3(WOOD_DARK);  glVertex3f(mx,my,mz)
        c3(lerpRGB(WOOD_DARK,(0.10,0.07,0.04),0.5)); glVertex3f(ex,ey,ez)
        glEnd()
        glBegin(GL_LINES)
        c3(WOOD_DARK)
        glVertex3f(mx,my,mz); glVertex3f(mx+ex*0.22,my+0.5,mz+ez*0.3)
        glEnd()
    glLineWidth(1.0)


# ═══════════════════════════════════════════════
# Fantasma
# ═══════════════════════════════════════════════
def draw_ghost(sway_deg):
    # Corpo oval com balanço e escala vertical
    glPushMatrix()
    glRotatef(sway_deg,0,0,1)
    glScalef(1.0,1.35,0.65)
    segs=24
    glBegin(GL_TRIANGLE_FAN)
    c3(GHOST_CTR); glVertex2f(0,0)
    for i in range(segs+1):
        a=2*math.pi*i/segs
        t=0.5+0.5*math.sin(a*2)
        c3(lerpRGB(GHOST_EDGE,GHOST_CTR,t*0.5))
        glVertex2f(math.cos(a)*0.52, math.sin(a)*0.52)
    glEnd()
    glPopMatrix()

    # Brilho interno
    glBegin(GL_TRIANGLE_FAN)
    glColor3f(1.0,1.0,0.96); glVertex3f(0,0.08,0.01)
    for i in range(16):
        a=2*math.pi*i/16
        glColor3f(0.82,0.95,0.88)
        glVertex3f(math.cos(a)*0.22, 0.08+math.sin(a)*0.26, 0.01)
    glEnd()

    # Olhos
    for ex in [-0.16,0.16]:
        glPushMatrix(); glTranslatef(ex,0.18,0.35); glScalef(1.0,1.3,1.0)
        glBegin(GL_TRIANGLE_FAN)
        glColor3f(0.04,0.12,0.08); glVertex2f(0,0)
        for i in range(10):
            a=2*math.pi*i/10
            glVertex2f(math.cos(a)*0.08, math.sin(a)*0.08)
        glEnd()
        glPopMatrix()
        # Reflexo
        glPushMatrix(); glTranslatef(ex+0.03,0.22,0.36)
        glBegin(GL_TRIANGLE_FAN)
        glColor3f(0.9,1.0,0.95); glVertex2f(0,0)
        for i in range(6):
            a=2*math.pi*i/6
            glVertex2f(math.cos(a)*0.025, math.sin(a)*0.025)
        glEnd()
        glPopMatrix()

    # Cauda esfarrapada
    rags=[
        (-0.42,-0.50, -0.28,-0.80),
        (-0.20,-0.50, -0.14,-0.82),
        ( 0.02,-0.50,  0.08,-0.78),
        ( 0.22,-0.50,  0.30,-0.76),
    ]
    for (x0,y0,x2,y2) in rags:
        glBegin(GL_TRIANGLES)
        c3(GHOST_CTR);  glVertex3f(x0,    y0,0)
        c3(GHOST_CTR);  glVertex3f(x0+0.20,y0,0)
        c3(lerpRGB(GHOST_EDGE,(0,0,0),0.4)); glVertex3f(x2+0.10,y2,0)
        glEnd()


# ═══════════════════════════════════════════════
# Névoa
# ═══════════════════════════════════════════════
def draw_fog(t):
    wisps=[(-4.5,-1.5,3.2,0.55),(2.0,-3.0,2.8,0.45),
           (-1.0, 4.5,2.2,0.50),(5.5,-2.5,3.5,0.60),(-0.5,1.0,2.0,0.40)]
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    for idx,(wx,wz,wr,alpha) in enumerate(wisps):
        dx=math.sin(t*0.30+idx*1.7)*0.6
        dz=math.cos(t*0.22+idx*2.1)*0.4
        pa=alpha*(0.75+0.25*math.sin(t*0.5+idx))
        glPushMatrix()
        glTranslatef(wx+dx,0.06,wz+dz)
        glScalef(wr,0.15,wr*0.45)
        segs=18
        glBegin(GL_TRIANGLE_FAN)
        glColor4f(*FOG_COLOR[:3],pa); glVertex3f(0,0,0)
        for i in range(segs+1):
            a=2*math.pi*i/segs
            glColor4f(*FOG_COLOR[:3],0.0)
            glVertex3f(math.cos(a),0,math.sin(a))
        glEnd()
        glPopMatrix()
    glDisable(GL_BLEND)


# ═══════════════════════════════════════════════
# Renderização
# ═══════════════════════════════════════════════
def render():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    yr=math.radians(cam["yaw"]); pr=math.radians(cam["pitch"])
    lx=cam["x"]+math.sin(yr)*math.cos(pr)
    ly=cam["y"]+math.sin(pr)
    lz=cam["z"]-math.cos(yr)*math.cos(pr)
    gluLookAt(cam["x"],cam["y"],cam["z"], lx,ly,lz, 0,1,0)

    draw_sky_backdrop()

    glDepthMask(GL_FALSE)
    draw_stars(anim["time"])
    glDepthMask(GL_TRUE)

    # Lua (billboard simples: zera rotação da matrix)
    glPushMatrix()
    glTranslatef(4.5,11.5,-20.0)
    m=(GLfloat*16)()
    glGetFloatv(GL_MODELVIEW_MATRIX,m)
    for i in range(3):
        for j in range(3):
            m[i*4+j]=1.0 if i==j else 0.0
    glLoadMatrixf(m)
    glTranslatef(4.5,11.5,-20.0)
    draw_moon_with_halo(anim["moon_pulse"])
    glPopMatrix()

    draw_ground()
    draw_fog(anim["time"])

    # Túmulos
    graves=[
        (-3.8,0,-1.8, 12,1.00,1.00),
        ( 0.2,0,-3.8, -6,0.88,1.30),
        ( 3.6,0,-1.4, 18,1.15,0.80),
        (-1.2,0,-6.2,  3,1.00,1.10),
        ( 2.8,0,-6.8,-10,0.80,0.95),
    ]
    for (tx,ty,tz,ry,sx,sy) in graves:
        glPushMatrix()
        glTranslatef(tx,ty,tz)
        glRotatef(ry,0,1,0)
        draw_grave(sx,sy)
        glPopMatrix()

    # ══ MÃOS DE ZUMBI ══
    prog = anim["zombie_progress"]
    if anim["zombie_phase"] != "idle" or prog > 0.0:
        # Cada mão emerge de perto de um túmulo; offset lateral para variar
        hand_positions = [
            (-3.8 - 0.18, -1.2),   # túmulo 0 – mão esquerda
            (-3.8 + 0.18, -1.6),   # túmulo 0 – mão direita
            ( 0.2 - 0.18, -3.2),   # túmulo 1
            ( 0.2 + 0.20, -3.6),
            ( 3.6 - 0.15, -0.9),   # túmulo 2
            ( 3.6 + 0.18, -1.3),
            (-1.2 - 0.16, -5.8),   # túmulo 3
            (-1.2 + 0.20, -6.2),
            ( 2.8 - 0.18, -6.4),   # túmulo 4
            ( 2.8 + 0.18, -6.8),
        ]
        # Mãos pares inclinam à esquerda, ímpares à direita
        tilts = [-18, 15, -12, 20, -16, 14, -20, 18, -14, 16]
        # Altura máxima que emerge do chão (topo da mão visível)
        MAX_EMERGE = 0.9   # metros acima do chão
        emerge_y = prog * MAX_EMERGE - MAX_EMERGE  # de -MAX_EMERGE a 0

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for idx, ((hx, hz), tilt) in enumerate(zip(hand_positions, tilts)):
            glPushMatrix()
            glTranslatef(hx, emerge_y, hz)
            glRotatef(tilt, 0, 0, 1)        # inclinação lateral única
            glRotatef(idx * 37 % 30 - 15, 0, 1, 0)  # pequena rotação em Y

            # Clip no chão: esconde a parte subterrânea via translação
            # (a mão é desenhada em y=0..total; glClipPlane recorta abaixo do chão)
            glEnable(GL_CLIP_PLANE0)
            plane_eq = (GLdouble * 4)(0.0, 1.0, 0.0, -emerge_y)  # y >= -emerge_y
            glClipPlane(GL_CLIP_PLANE0, plane_eq)

            draw_zombie_hand(anim["time"], hand_id=idx)

            glDisable(GL_CLIP_PLANE0)
            glPopMatrix()
        glDisable(GL_BLEND)

    # Árvores
    trees=[(-7.0,-1.5,1.00,4.4),(6.5,-2.5,0.82,3.9),
           ( 1.8,-9.5,1.15,5.0),(-4.5,-8.0,0.90,4.2)]
    for (tx,tz,sc,ht) in trees:
        glPushMatrix()
        glTranslatef(tx,0,tz)
        glScalef(sc,sc,sc)
        draw_dead_tree(ht)
        glPopMatrix()

    # ══ FANTASMA (composição de transformações) ══
    fy   = 0.30*math.sin(anim["ghost_float"])   # flutuação
    sway = 7.0 *math.sin(anim["ghost_sway"])    # balanço

    glPushMatrix()
    glTranslatef(ghost_pos["x"],ghost_pos["y"],ghost_pos["z"])  # 1. posição do usuário
    glTranslatef(0.0, fy, 0.0)                                  # 2. flutuação animada
    glScalef(0.85,0.85,0.85)                                    # 3. escala real
    draw_ghost(sway)                                            # 4. rotação interna
    glPopMatrix()


# ═══════════════════════════════════════════════
# Atualização
# ═══════════════════════════════════════════════
def update(dt):
    if anim["paused"]: return
    anim["time"]        +=dt
    anim["ghost_float"] +=1.6*dt
    anim["ghost_sway"]  +=1.1*dt
    anim["moon_pulse"]  +=0.9*dt

    # ── Máquina de estado das mãos de zumbi ──
    RISE_SPEED = 0.28   # unidades de progresso por segundo (devagar)
    HOLD_TIME  = 1.8    # segundos parado no topo
    SINK_SPEED = 0.45   # desce um pouco mais rápido

    phase = anim["zombie_phase"]
    if phase == "rising":
        anim["zombie_progress"] += RISE_SPEED * dt
        if anim["zombie_progress"] >= 1.0:
            anim["zombie_progress"] = 1.0
            anim["zombie_phase"]    = "holding"
            anim["zombie_hold_t"]   = 0.0
    elif phase == "holding":
        anim["zombie_hold_t"] = anim.get("zombie_hold_t", 0.0) + dt
        if anim["zombie_hold_t"] >= HOLD_TIME:
            anim["zombie_phase"] = "sinking"
    elif phase == "sinking":
        anim["zombie_progress"] -= SINK_SPEED * dt
        if anim["zombie_progress"] <= 0.0:
            anim["zombie_progress"] = 0.0
            anim["zombie_phase"]    = "idle"


# ═══════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════
def main():
    if not glfw.init():
        print("Erro ao inicializar GLFW"); sys.exit(1)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR,2)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR,1)
    window=glfw.create_window(WINDOW_W,WINDOW_H,"Cemiterio Assombrado - ICG 2025",None,None)
    if not window:
        glfw.terminate(); print("Erro ao criar janela"); sys.exit(1)
    glfw.make_context_current(window)
    glfw.swap_interval(1)
    glfw.set_key_callback(window,key_callback)
    glfw.set_framebuffer_size_callback(window,framebuffer_size_callback)
    glEnable(GL_DEPTH_TEST)
    glClearColor(*SKY_TOP,1.0)
    glViewport(0,0,WINDOW_W,WINDOW_H)
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(48.0,WINDOW_W/WINDOW_H,0.1,200.0)
    glMatrixMode(GL_MODELVIEW)

    print("="*56)
    print("  CEMITERIO ASSOMBRADO — ICG 2025")
    print("="*56)
    print("  Câmera :  W/S/A/D mover  |  Q/E cima/baixo")
    print("            Setas ←→ girar |  ↑↓  inclinar")
    print("  Fantasma: I/K frente/trás|  J/L lados  |  U/O cima/baixo")
    print("  M mãos de zumbi  |  P pausar  |  R resetar  |  ESC sair")
    print("="*56)

    last=glfw.get_time()
    while not glfw.window_should_close(window):
        now=glfw.get_time(); dt=now-last; last=now
        glfw.poll_events()
        process_keys()
        update(dt)
        render()
        glfw.swap_buffers(window)
    glfw.terminate()

if __name__=="__main__":
    main()