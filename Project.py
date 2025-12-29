import math
import random
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# =========================
# 1️⃣ GLOBAL GAME STATE
# =========================
GAME_PLAYING, GAME_PAUSED, GAME_OVER = 0, 1, 2
game_state = GAME_PLAYING

score, difficulty = 0, 0
health_booster_pos = {'x': 0, 'y': 0, 'pulse': 0.0, 'radius': 25.0}

# =========================
# 2️⃣ CORE SYSTEM & PLAYER
# =========================
PLAYER_MAX_HP = 500
player_hp = PLAYER_MAX_HP
player_radius = 25.0
GUN_LENGTH = 55.0

player_x, player_y = 0.0, -150.0
gun_angle = 0.0

# Movement settings - smoother forward/backward
MOVE_STEP = 18.0      # Larger step for smoother movement
TURN_STEP = 2.5       # Small angle for precise aiming

mouse_state = {GLUT_LEFT_BUTTON: GLUT_UP}

CAM_ORBIT, CAM_TURRET_FOLLOW, CAM_FIRST_PERSON = range(3)
camera_mode = CAM_TURRET_FOLLOW
camera_angle, camera_height_offset = 0.0, 0

# =========================
# 2.5️⃣ WEAPON DATA
# =========================
WEAPON_NORMAL, WEAPON_LASER, WEAPON_BURST, WEAPON_SHOCKWAVE = range(4)
current_weapon = WEAPON_NORMAL

WEAPON_STATS = {
    WEAPON_NORMAL:   {"damage": 50},
    WEAPON_LASER:    {"damage": 2.5},
    WEAPON_BURST:    {"damage": 45},
    WEAPON_SHOCKWAVE:{"damage": 100},
}
fire_cooldown = 0
FIRE_CD_NORMAL, FIRE_CD_LASER, FIRE_CD_BURST, FIRE_CD_SHOCKWAVE = 10, 1, 5, 40
burst_remaining = 0

laser_beam_active, laser_target_pos = False, (0, 0, 0)
bullets, bullet_speed = [], 15.0

# =========================
# 3️⃣ ENEMY DATA MODEL
# =========================
enemies, enemy_bullets = [], []
enemy_pulse, CONTACT_COOLDOWN = 0.0, 30

# REMOVED Type 5 (Brute) - Only 5 enemy types now (0-4)
# All enemies stop at safe distance EXCEPT Type 4 (Kamikaze) which touches player
ENEMY_STATS = {
    0: {"hp": 60,  "speed": 1.8, "stop_dist": 120,   "fire_rate": 180, "bullet_speed": 4, "bullet_damage": 10, "radius": 20, "contact_damage": 0, "kamikaze_damage": 0},
    1: {"hp": 200, "speed": 0.8, "stop_dist": 220,   "fire_rate": 300, "bullet_speed": 6, "bullet_damage": 40, "radius": 40, "contact_damage": 0, "kamikaze_damage": 0},
    2: {"hp": 60,  "speed": 1.2, "stop_dist": 130,   "fire_rate": 140, "bullet_speed": 5, "bullet_damage": 15, "radius": 20, "contact_damage": 0, "kamikaze_damage": 0},
    3: {"hp": 50,  "speed": 0.0, "stop_dist": 0,     "fire_rate": 360, "bullet_speed": 20,"bullet_damage": 75, "radius": 20, "contact_damage": 0, "kamikaze_damage": 0},
    4: {"hp": 50,  "speed": 2.5, "stop_dist": 5,     "fire_rate": 9999,"bullet_speed": 0, "bullet_damage": 0,  "radius": 25, "contact_damage": 0, "kamikaze_damage": 150},
}
GRID_LENGTH, fovY = 1800, 90

# =========================
# 🌲 SCENERY DATA
# =========================
tree_positions = []
pond_data = {'x': 250, 'y': 200, 'radius': 90}
TREE_RADIUS, POND_RADIUS = 15.0, pond_data['radius']

# =========================
# Math & Rendering Helpers
# =========================
def sin_approx(x):
    while x > 3.14159: x -= 6.28318
    while x < -3.14159: x += 6.28318
    x2 = x * x
    return x - x*x2/6.0 + x*x2*x2/120.0

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def check_line_of_sight(start_pos, end_pos):
    p1x, p1y = start_pos
    p2x, p2y = end_pos
    dx, dy = p2x - p1x, p2y - p1y
    line_len_sq = dx*dx + dy*dy
    if line_len_sq == 0:
        return True
    for tx, ty, _ in tree_positions:
        t = max(0, min(1, ((tx - p1x) * dx + (ty - p1y) * dy) / line_len_sq))
        closest_x, closest_y = p1x + t * dx, p1y + t * dy
        if (tx - closest_x)**2 + (ty - closest_y)**2 < (TREE_RADIUS + 5)**2:
            return False
    return True

# =========================
# 🔟 HUD & Drawing
# =========================
def draw_hud():
    hp_ratio = max(0, player_hp / PLAYER_MAX_HP)
    if hp_ratio > 0.6:
        glColor3f(0.2, 1.0, 0.2)
    elif hp_ratio > 0.3:
        glColor3f(1.0, 1.0, 0.2)
    else:
        glColor3f(1.0, 0.2, 0.2)
    draw_text(10, 760, f"Player HP: {int(player_hp)} / {PLAYER_MAX_HP}")
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    bar_x, bar_y, bar_w, bar_h = 10, 750, 200, 8
    glColor3f(0.5, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(bar_x, bar_y, 0)
    glVertex3f(bar_x + bar_w, bar_y, 0)
    glVertex3f(bar_x + bar_w, bar_y + bar_h, 0)
    glVertex3f(bar_x, bar_y + bar_h, 0)
    glEnd()
    
    if hp_ratio > 0.6:
        glColor3f(0.2, 1.0, 0.2)
    elif hp_ratio > 0.3:
        glColor3f(1.0, 1.0, 0.2)
    else:
        glColor3f(1.0, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(bar_x, bar_y, 0)
    glVertex3f(bar_x + bar_w * hp_ratio, bar_y, 0)
    glVertex3f(bar_x + bar_w * hp_ratio, bar_y + bar_h, 0)
    glVertex3f(bar_x, bar_y + bar_h, 0)
    glEnd()
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    
    glColor3f(1, 1, 1)
    draw_text(10, 730, f"Score: {score}")
    draw_text(10, 705, f"Difficulty Level: {difficulty}")

    weapon_names = ["Normal", "Laser", "Burst", "Shockwave"]
    draw_text(800, 60, "Weapon: " + weapon_names[current_weapon] + " (1-4)")
    cam_name = ["Orbit", "Turret Follow", "First Person"][camera_mode]
    draw_text(800, 30, "Camera: " + cam_name + " (Q)")
    
    if game_state == GAME_PAUSED:
        draw_text(350, 400, "PAUSED - PRESS SPACE TO RESUME")
        draw_text(390, 370, "PRESS R TO RESTART")
    elif game_state == GAME_OVER:
        draw_text(400, 400, "GAME OVER - PRESS R")

def create_scenery(num_trees=150):
    tree_positions.clear()
    for _ in range(num_trees):
        while True:
            buffer = 50.0
            x = random.uniform(-GRID_LENGTH+buffer, GRID_LENGTH-buffer)
            y = random.uniform(-GRID_LENGTH+buffer, GRID_LENGTH-buffer)
            if math.hypot(x, y) > 200 and math.hypot(x-pond_data['x'], y-pond_data['y']) > POND_RADIUS+TREE_RADIUS:
                tree_positions.append((x, y, random.uniform(0.8, 1.5)))
                break

def draw_pond():
    glPushMatrix()
    glTranslatef(pond_data['x'], pond_data['y'], 0.1)
    glColor3f(0.2, 0.4, 0.7)
    glBegin(GL_POLYGON)
    for i in range(33):
        angle = (i / 32) * 2 * math.pi
        px = POND_RADIUS * math.cos(angle)
        py = POND_RADIUS * math.sin(angle)
        glVertex3f(px, py, 0)
    glEnd()
    glPopMatrix()

# ❤️ HEART-SHAPED HEALTH BOOSTER
def draw_health_booster():
    bx = health_booster_pos['x']
    by = health_booster_pos['y']
    b_pulse = health_booster_pos['pulse']
    
    glPushMatrix()
    glTranslatef(bx, by, 35)
    
    pulse_scale = 1.0 + 0.2 * sin_approx(b_pulse)
    glScalef(pulse_scale, pulse_scale, pulse_scale)
    
    glRotatef(b_pulse * 30, 0, 0, 1)
    
    glColor3f(1.0, 0.1, 0.1)
    
    q = gluNewQuadric()
    
    glPushMatrix()
    glTranslatef(-7, 0, 5)
    gluSphere(q, 9, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(7, 0, 5)
    gluSphere(q, 9, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(0, 0, 5)
    glRotatef(180, 1, 0, 0)
    gluCylinder(q, 14, 0, 22, 12, 1)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(0, 0, 3)
    gluSphere(q, 7, 10, 10)
    glPopMatrix()
    
    glPopMatrix()

def draw_boundary_walls():
    WALL_HEIGHT = 200.0
    glColor3f(0.3, 0.3, 0.35)
    glBegin(GL_QUADS)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, WALL_HEIGHT)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, WALL_HEIGHT)
    
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, WALL_HEIGHT)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, WALL_HEIGHT)
    
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, WALL_HEIGHT)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, WALL_HEIGHT)
    
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, WALL_HEIGHT)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, WALL_HEIGHT)
    glEnd()

def draw_environment():
    glColor3f(0.45, 0.30, 0.15)
    glBegin(GL_QUADS)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glEnd()
    
    draw_pond()
    for pos in tree_positions:
        draw_tree(pos)
    draw_boundary_walls()

def draw_tree(position):
    x, y, scale = position
    glPushMatrix()
    glTranslatef(x, y, 0)
    glScalef(scale, scale, scale)
    
    glColor3f(0.5, 0.35, 0.05)
    q = gluNewQuadric()
    gluCylinder(q, 8, 8, 40, 10, 1)
    
    glColor3f(0.1, 0.6, 0.2)
    glTranslatef(0, 0, 35)
    gluCylinder(q, 25, 0, 50, 15, 5)
    
    glPopMatrix()

def draw_turret():
    if camera_mode == CAM_FIRST_PERSON:
        return
    
    glPushMatrix()
    glTranslatef(player_x, player_y, 0)
    glRotatef(gun_angle, 0, 0, 1)
    
    q = gluNewQuadric()

    glColor3f(0.3, 0.3, 0.8)
    gluCylinder(q, 15, 15, 40, 10, 10)
    
    glPushMatrix()
    glTranslatef(0, 0, 40)
    glColor3f(0.9, 0.7, 0.6)
    gluSphere(q, 18, 12, 12)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(0, 0, 55)
    glColor3f(0.2, 0.2, 0.6)
    gluCylinder(q, 17, 15, 8, 12, 1)
    glTranslatef(0, 0, 8)
    glBegin(GL_POLYGON)
    for i in range(12):
        angle = (i / 12) * 2 * math.pi
        glVertex3f(15 * math.cos(angle), 15 * math.sin(angle), 0)
    glEnd()
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0, 0, 40)
    glColor3f(0.4, 0.4, 0.7)
    glPushMatrix()
    glTranslatef(-20, 0, 0)
    glRotatef(90, 0, 1, 0)
    gluCylinder(q, 4, 4, 10, 8, 1)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(20, 0, 0)
    glRotatef(-90, 0, 1, 0)
    gluCylinder(q, 4, 4, 10, 8, 1)
    glPopMatrix()
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0, 0, 50)
    glColor3f(0.2, 0.2, 0.2)
    glRotatef(90, 0, 1, 0)
    gluCylinder(q, 5, 5, GUN_LENGTH, 10, 10)
    glTranslatef(0, 0, GUN_LENGTH)
    glColor3f(0.5, 0.5, 0.5)
    glutSolidCube(8)
    glPopMatrix()

    glPopMatrix()

def draw_enemy(enemy, pulse):
    x, y, z, etype = enemy[0], enemy[1], enemy[2], enemy[3]
    hp, max_hp = enemy[4], enemy[5]
    
    glPushMatrix()
    glTranslatef(x, y, 0)
    
    if etype != 3:
        glRotatef(math.degrees(math.atan2(player_y - y, player_x - x)), 0, 0, 1)
    
    pulse_scale = 1 + 0.1 * sin_approx(pulse)
    glScalef(pulse_scale, pulse_scale, pulse_scale)
    
    hp_ratio = hp / max_hp
    
    if etype == 1:
        draw_tank(hp_ratio)
    elif etype in (0, 2, 3):
        draw_soldier(etype, hp_ratio)
    elif etype == 4:
        # Kamikaze enemy (magenta cube)
        glPushMatrix()
        glTranslatef(0, 0, 30)
        glColor3f(1.0 * hp_ratio, 0.0, 1.0 * hp_ratio)
        glScalef(1.5, 1.5, 1.5)
        glutSolidCube(25)
        glPopMatrix()
    
    glPopMatrix()

def draw_bullet(b):
    kind = b[6]
    if kind in ("normal", "burst"):
        x, y, z = b[0], b[1], b[2]
        glPushMatrix()
        glTranslatef(x, y, z)
        glColor3f(1, 1, 0)
        glutSolidCube(5)
        glPopMatrix()
    elif kind == "shockwave":
        radius = b[7]
        x, y = b[0], b[1]
        glPushMatrix()
        glTranslatef(x, y, 2.0)
        glColor3f(1.0, 0.7, 0.2)
        glBegin(GL_LINE_LOOP)
        for i in range(32):
            angle = (6.28 * i) / 32
            glVertex3f(radius * math.cos(angle), radius * math.sin(angle), 0)
        glEnd()
        glPopMatrix()

def draw_enemy_bullet(b):
    x, y, z, etype = b[0], b[1], b[2], b[6]
    colors = {0: (1.0, 0.2, 0.2), 1: (1.0, 0.5, 0.0), 2: (0.1, 1.0, 0.1), 3: (1.0, 1.0, 0.0)}
    color = colors.get(etype, (1.0, 1.0, 1.0))
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(color[0], color[1], color[2])
    q = gluNewQuadric()
    gluSphere(q, 4, 6, 6)
    glPopMatrix()

def draw_soldier(etype, hp_ratio):
    if etype == 0:
        uniform_color = [1.0 * hp_ratio, 0.2 * hp_ratio, 0.2 * hp_ratio]
    elif etype == 2:
        uniform_color = [0.9 * hp_ratio, 0.7 * hp_ratio, 0.1 * hp_ratio]
    else:
        uniform_color = [0.6 * hp_ratio, 0.6 * hp_ratio, 1.0 * hp_ratio]
    
    glRotatef(-90, 0, 0, 1)
    
    glPushMatrix()
    glColor3f(uniform_color[0], uniform_color[1], uniform_color[2])
    glScalef(0.6, 1.0, 0.5)
    glTranslatef(0, 0, 45)
    glutSolidCube(25)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0.3 * hp_ratio, 0.35 * hp_ratio, 0.3 * hp_ratio)
    glTranslatef(0, 13, 45)
    glScalef(0.7, 0.2, 0.8)
    glutSolidCube(20)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0.25 * hp_ratio, 0.3 * hp_ratio, 0.25 * hp_ratio)
    glTranslatef(0, 0, 68)
    q = gluNewQuadric()
    gluSphere(q, 12, 10, 10)
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(0.9, 0.7, 0.6)
    glTranslatef(0, 7, 66)
    glScalef(0.9, 0.7, 0.6)
    gluSphere(q, 10, 10, 10)
    glPopMatrix()
    
    for i in [-1, 1]:
        glPushMatrix()
        glColor3f(uniform_color[0], uniform_color[1], uniform_color[2])
        glTranslatef(i * 8, 0, 20)
        glScalef(0.5, 0.5, 1.5)
        glutSolidCube(20)
        glColor3f(0.2 * hp_ratio, 0.2 * hp_ratio, 0.2 * hp_ratio)
        glTranslatef(0, 0, -12)
        glScalef(1.2, 1.2, 0.4)
        glutSolidCube(20)
        glPopMatrix()
    
    if etype == 3:
        glPushMatrix()
        glColor3f(0.1, 0.1, 0.1)
        glTranslatef(15, 20, 45)
        glRotatef(90, 0, 1, 0)
        glRotatef(-15, 1, 0, 0)
        q = gluNewQuadric()
        gluCylinder(q, 2, 2, 50, 6, 1)
        glTranslatef(0, 0, -5)
        glScalef(1, 1, 1.5)
        glutSolidCube(6)
        glPopMatrix()

def draw_enemy_health_bar(enemy):
    x, y, z, etype, hp, max_hp = enemy[0], enemy[1], enemy[2], enemy[3], enemy[4], enemy[5]
    if hp >= max_hp:
        return
    
    glPushMatrix()
    
    if etype == 1:
        height_offset = 80
    else:
        height_offset = 100
    
    glTranslatef(x, y, z + height_offset)
    
    bar_width = 40
    bar_height = 6
    hp_ratio = hp / max_hp
    
    glColor3f(0.0, 0.0, 0.0)
    glBegin(GL_QUADS)
    glVertex3f(-bar_width/2, -bar_height/2, 0)
    glVertex3f(bar_width/2, -bar_height/2, 0)
    glVertex3f(bar_width/2, bar_height/2, 0)
    glVertex3f(-bar_width/2, bar_height/2, 0)
    glEnd()
    
    if hp_ratio > 0.6:
        glColor3f(0.1, 0.9, 0.1)
    elif hp_ratio > 0.3:
        glColor3f(0.9, 0.9, 0.1)
    else:
        glColor3f(0.9, 0.1, 0.1)
    
    glBegin(GL_QUADS)
    glVertex3f(-bar_width/2, -bar_height/2, 0.1)
    glVertex3f(-bar_width/2 + bar_width * hp_ratio, -bar_height/2, 0.1)
    glVertex3f(-bar_width/2 + bar_width * hp_ratio, bar_height/2, 0.1)
    glVertex3f(-bar_width/2, bar_height/2, 0.1)
    glEnd()
    
    glPopMatrix()

def draw_tank(hp_ratio):
    main_color = [1.0 * hp_ratio, 1.0 * hp_ratio, 1.0 * hp_ratio]
    track_color = [0.2 * hp_ratio, 0.2 * hp_ratio, 0.2 * hp_ratio]
    
    glRotatef(-90, 0, 0, 1)
    
    glPushMatrix()
    glColor3f(main_color[0], main_color[1], main_color[2])
    glTranslatef(0, 0, 20)
    glScalef(1.0, 1.8, 0.5)
    glutSolidCube(40)
    glPopMatrix()
    
    for i in [-1, 1]:
        glPushMatrix()
        glColor3f(track_color[0], track_color[1], track_color[2])
        glTranslatef(i * 25, 0, 15)
        glScalef(0.3, 2.0, 0.6)
        glutSolidCube(40)
        glPopMatrix()
    
    glPushMatrix()
    glColor3f(main_color[0], main_color[1], main_color[2])
    glTranslatef(0, 0, 45)
    q = gluNewQuadric()
    gluCylinder(q, 18, 18, 12, 15, 5)
    glTranslatef(0, 0, 12)
    glBegin(GL_POLYGON)
    for i in range(15):
        angle = (6.28 * i) / 15
        glVertex3f(18 * math.cos(angle), 18 * math.sin(angle), 0)
    glEnd()
    glPopMatrix()
    
    glPushMatrix()
    glColor3f(track_color[0], track_color[1], track_color[2])
    glTranslatef(0, 20, 50)
    gluCylinder(q, 4, 3, 70, 8, 2)
    glPopMatrix()

# ===============================================
# 4️⃣-9️⃣ LOGIC & UPDATE LOOPS
# ===============================================
def move_health_booster():
    while True:
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(300, GRID_LENGTH - 200)
        bx = dist * math.cos(angle)
        by = dist * math.sin(angle)
        valid = True
        for tx, ty, _ in tree_positions:
            if math.hypot(bx - tx, by - ty) < TREE_RADIUS + health_booster_pos['radius']:
                valid = False
                break
        if valid:
            health_booster_pos['x'] = bx
            health_booster_pos['y'] = by
            break

def is_gun_tip_valid(gun_tip_x, gun_tip_y):
    if not (-GRID_LENGTH + 5 < gun_tip_x < GRID_LENGTH - 5 and -GRID_LENGTH + 5 < gun_tip_y < GRID_LENGTH - 5):
        return False
    for tx, ty, _ in tree_positions:
        if math.hypot(gun_tip_x - tx, gun_tip_y - ty) < TREE_RADIUS:
            return False
    for e in enemies:
        if math.hypot(gun_tip_x - e[0], gun_tip_y - e[1]) < ENEMY_STATS[e[3]]['radius']:
            return False
    return True

def is_position_valid_for_player(x, y):
    for tx, ty, _ in tree_positions:
        if math.hypot(x - tx, y - ty) < player_radius + TREE_RADIUS:
            return False
    return -GRID_LENGTH + player_radius < x < GRID_LENGTH - player_radius and -GRID_LENGTH + player_radius < y < GRID_LENGTH - player_radius

def is_position_valid_for_enemy_static(x, y, radius):
    for tx, ty, _ in tree_positions:
        if math.hypot(x - tx, y - ty) < radius + TREE_RADIUS:
            return False
    return -GRID_LENGTH + radius < x < GRID_LENGTH - radius and -GRID_LENGTH + radius < y < GRID_LENGTH - radius

def try_move_player(direction):
    """Smoother forward/backward movement with larger steps"""
    global player_x, player_y
    
    angle_rad = math.radians(gun_angle)
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    
    if direction == 'forward':
        dx, dy = cos_a * MOVE_STEP, sin_a * MOVE_STEP
    elif direction == 'backward':
        dx, dy = -cos_a * MOVE_STEP, -sin_a * MOVE_STEP
    else:
        return
    
    next_x = player_x + dx
    next_y = player_y + dy
    
    if is_position_valid_for_player(next_x, player_y):
        player_x = next_x
    
    if is_position_valid_for_player(player_x, next_y):
        player_y = next_y

def try_rotate_gun(direction):
    """Small angle steps for precise aiming"""
    global gun_angle
    
    if direction == 'left':
        next_angle = gun_angle + TURN_STEP
    elif direction == 'right':
        next_angle = gun_angle - TURN_STEP
    else:
        return
    
    angle_rad = math.radians(next_angle)
    gun_tip_x = player_x + math.cos(angle_rad) * GUN_LENGTH
    gun_tip_y = player_y + math.sin(angle_rad) * GUN_LENGTH
    
    if is_gun_tip_valid(gun_tip_x, gun_tip_y):
        gun_angle = next_angle

def split_enemy(enemy):
    x, y = enemy[0], enemy[1]
    for _ in range(3):
        stats = ENEMY_STATS[0]
        off_x = random.uniform(-30, 30)
        off_y = random.uniform(-30, 30)
        new_hp = stats["hp"] * (1 + difficulty * 0.1)
        new_speed = stats["speed"] * (1 + difficulty * 0.05)
        enemies.append([x + off_x, y + off_y, 0, 0, new_hp, new_hp, new_speed, 0, stats["fire_rate"], 0, 0, 0])

def manage_enemy_spawning():
    global difficulty
    difficulty = score // 30
    max_enemies = 8 + difficulty * 2
    
    if len(enemies) < max_enemies:
        # Only spawn enemy types 0-4 (removed type 5)
        etype = random.choices([0, 1, 2, 3, 4], weights=[10, 2, 4, 1, 8], k=1)[0]
        stat = ENEMY_STATS[etype]
        
        while True:
            angle = random.uniform(0, 2 * math.pi)
            spawn_dist = GRID_LENGTH - stat['radius'] - 100
            spawn_x = spawn_dist * math.cos(angle)
            spawn_y = spawn_dist * math.sin(angle)
            
            if is_position_valid_for_enemy_static(spawn_x, spawn_y, stat['radius']):
                if etype == 3:
                    if check_line_of_sight((spawn_x, spawn_y), (0, 0)):
                        break
                else:
                    break
        
        hp = stat["hp"] * (1 + difficulty * 0.15)
        speed = stat["speed"] * (1 + difficulty * 0.08)
        enemies.append([spawn_x, spawn_y, 0, etype, hp, hp, speed, 0, random.randint(0, stat["fire_rate"]), 0, 0, 0])

def initial_spawn():
    enemies.clear()
    spawn_types = {1: 3, 0: 4}
    
    for etype, count in spawn_types.items():
        for i in range(count):
            stat = ENEMY_STATS[etype]
            while True:
                angle = random.uniform(0, 2 * math.pi)
                spawn_dist = random.uniform(GRID_LENGTH - 600, GRID_LENGTH - 200)
                spawn_x = spawn_dist * math.cos(angle)
                spawn_y = spawn_dist * math.sin(angle)
                if is_position_valid_for_enemy_static(spawn_x, spawn_y, stat['radius']):
                    break
            enemies.append([spawn_x, spawn_y, 0, etype, stat['hp'], stat['hp'], stat['speed'], 0, random.randint(0, stat["fire_rate"]), 0, 0, 0])

def update_enemies():
    global score, player_hp
    
    for i, e in enumerate(enemies):
        if e[4] <= 0:
            etype = e[3]
            if etype == 1:
                score += 30
            elif etype == 2:
                score += 15
                split_enemy(e)
            elif etype == 4:
                score += 10
            else:
                score += 5
            enemies.pop(i)
            continue
        
        if e[7] > 0:
            e[7] -= 1
            continue
        
        if e[9] > 0:
            e[9] -= 1
        
        stats = ENEMY_STATS[e[3]]
        dx = player_x - e[0]
        dy = player_y - e[1]
        dist_to_player = math.hypot(dx, dy) if math.hypot(dx, dy) > 0 else 0.01
        
        # Only Kamikaze (type 4) can touch and explode on player
        if e[3] == 4 and dist_to_player < stats['radius'] + player_radius + 10:
            player_hp -= stats['kamikaze_damage']
            e[4] = 0
            continue
        
        # Smart pathfinding - enemies stop at stop_dist
        if stats["speed"] > 0 and dist_to_player > stats["stop_dist"]:
            base_speed = e[6]
            
            norm_dx = dx / dist_to_player
            norm_dy = dy / dist_to_player
            
            perp_left_x = -norm_dy
            perp_left_y = norm_dx
            perp_right_x = norm_dy
            perp_right_y = -norm_dx
            
            directions = [
                (norm_dx, norm_dy, "forward"),
                (perp_left_x, perp_left_y, "left"),
                (perp_right_x, perp_right_y, "right"),
                (-norm_dx, -norm_dy, "backward")
            ]
            
            for dir_x, dir_y, dir_name in directions:
                test_x = e[0] + dir_x * base_speed
                test_y = e[1] + dir_y * base_speed
                
                if is_position_valid_for_enemy_static(test_x, test_y, stats['radius']):
                    e[0] = test_x
                    e[1] = test_y
                    break
        
        # Firing logic
        e[8] -= 1
        if e[8] <= 0 and stats['fire_rate'] < 9000 and check_line_of_sight((e[0], e[1]), (player_x, player_y)):
            e[8] = stats["fire_rate"]
            b_vx = (dx / dist_to_player) * stats["bullet_speed"]
            b_vy = (dy / dist_to_player) * stats["bullet_speed"]
            enemy_bullets.append([e[0], e[1], 30.0, b_vx, b_vy, stats["bullet_damage"], e[3]])

def resolve_collisions():
    global player_x, player_y
    
    for e in enemies:
        e_stats = ENEMY_STATS[e[3]]
        dist = math.hypot(player_x - e[0], player_y - e[1])
        min_dist = player_radius + e_stats['radius']
        
        if dist > 0 and dist < min_dist:
            overlap = min_dist - dist
            dx = (player_x - e[0]) / dist
            dy = (player_y - e[1]) / dist
            push_amount = overlap * 0.51
            player_x += dx * push_amount
            player_y += dy * push_amount
            e[0] -= dx * push_amount
            e[1] -= dy * push_amount
    
    for i in range(len(enemies)):
        for j in range(i + 1, len(enemies)):
            e1, e2 = enemies[i], enemies[j]
            e1_stats = ENEMY_STATS[e1[3]]
            e2_stats = ENEMY_STATS[e2[3]]
            dist = math.hypot(e1[0] - e2[0], e1[1] - e2[1])
            min_dist = e1_stats['radius'] + e2_stats['radius']
            
            if dist > 0 and dist < min_dist:
                overlap = min_dist - dist
                dx = (e1[0] - e2[0]) / dist
                dy = (e1[1] - e2[1]) / dist
                push_amount = overlap * 0.51
                e1[0] += dx * push_amount
                e1[1] += dy * push_amount
                e2[0] -= dx * push_amount
                e2[1] -= dy * push_amount

def update_game():
    global game_state, laser_beam_active, player_hp
    
    if player_hp <= 0:
        game_state = GAME_OVER
        player_hp = 0
        return
    
    if math.hypot(player_x - health_booster_pos['x'], player_y - health_booster_pos['y']) < player_radius + health_booster_pos['radius']:
        player_hp = PLAYER_MAX_HP
        move_health_booster()
    
    update_enemies()
    resolve_collisions()
    manage_enemy_spawning()
    
    laser_beam_active = False
    if current_weapon == WEAPON_LASER and mouse_state[GLUT_LEFT_BUTTON] == GLUT_DOWN:
        handle_laser()

def shoot_weapon():
    global fire_cooldown, burst_remaining
    
    if game_state != GAME_PLAYING or fire_cooldown > 0 or current_weapon == WEAPON_LASER:
        return
    
    angle_rad = math.radians(gun_angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    start_x = player_x + cos_a * GUN_LENGTH
    start_y = player_y + sin_a * GUN_LENGTH
    
    if current_weapon == WEAPON_NORMAL:
        bullets.append([start_x, start_y, 50.0, bullet_speed * cos_a, bullet_speed * sin_a, True, "normal"])
        fire_cooldown = FIRE_CD_NORMAL
    elif current_weapon == WEAPON_BURST:
        burst_remaining = 3
        fire_cooldown = FIRE_CD_BURST
    elif current_weapon == WEAPON_SHOCKWAVE:
        bullets.append([player_x, player_y, 0.0, 0, 0, True, "shockwave", 0.0])
        fire_cooldown = FIRE_CD_SHOCKWAVE

def handle_laser():
    global fire_cooldown, laser_beam_active, laser_target_pos
    
    if fire_cooldown > 0:
        return
    
    laser_beam_active = True
    fire_cooldown = FIRE_CD_LASER
    
    angle_rad = math.radians(gun_angle)
    dirx = math.cos(angle_rad)
    diry = math.sin(angle_rad)
    start_x = player_x + dirx * GUN_LENGTH
    start_y = player_y + diry * GUN_LENGTH
    max_range = 1500
    
    laser_target_pos = (start_x + dirx * max_range, start_y + diry * max_range, 50)
    
    closest_hit = (None, max_range)
    for enemy in enemies:
        dx = enemy[0] - start_x
        dy = enemy[1] - start_y
        t = dx * dirx + dy * diry
        
        if 0 < t < max_range:
            ex = start_x + t * dirx
            ey = start_y + t * diry
            if math.hypot(enemy[0] - ex, enemy[1] - ey) < ENEMY_STATS[enemy[3]]['radius'] and t < closest_hit[1]:
                closest_hit = (enemy, t)
    
    if closest_hit[0] is not None:
        hit_enemy = closest_hit[0]
        hit_enemy[4] -= WEAPON_STATS[WEAPON_LASER]["damage"]
        laser_target_pos = (hit_enemy[0], hit_enemy[1], 50)

def update_bullets():
    global bullets
    new_bullets = []
    
    for b in bullets:
        kind = b[6]
        
        if kind in ("normal", "burst"):
            x, y, z, vx, vy = b[0], b[1], b[2], b[3], b[4]
            x += vx
            y += vy
            
            if not (-GRID_LENGTH < x < GRID_LENGTH and -GRID_LENGTH < y < GRID_LENGTH):
                continue
            
            if not check_line_of_sight((x - vx, y - vy), (x, y)):
                continue
            
            hit = False
            for enemy in enemies:
                if math.hypot(x - enemy[0], y - enemy[1]) < ENEMY_STATS[enemy[3]]['radius']:
                    hit = True
                    damage = WEAPON_STATS[WEAPON_BURST if kind == "burst" else WEAPON_NORMAL]["damage"]
                    enemy[4] -= damage
                    break
            
            if not hit:
                new_bullets.append([x, y, z, vx, vy, True, kind])
        
        elif kind == "shockwave":
            x, y, z, radius = b[0], b[1], b[2], b[7]
            radius += 20
            
            if radius < 600:
                if int(radius) % 20 == 0:
                    for e in enemies:
                        if abs(math.hypot(e[0] - x, e[1] - y) - radius) < 20:
                            e[4] -= WEAPON_STATS[WEAPON_SHOCKWAVE]["damage"]
                new_bullets.append([x, y, z, 0, 0, True, kind, radius])
    
    bullets[:] = new_bullets

def update_enemy_bullets():
    global player_hp
    
    for b in enemy_bullets[:]:
        if not check_line_of_sight((b[0], b[1]), (b[0] + b[3], b[1] + b[4])):
            enemy_bullets.remove(b)
            continue
        
        b[0] += b[3]
        b[1] += b[4]
        
        if math.hypot(b[0] - player_x, b[1] - player_y) < player_radius:
            player_hp -= b[5]
            enemy_bullets.remove(b)
            continue
        
        if not (-GRID_LENGTH < b[0] < GRID_LENGTH and -GRID_LENGTH < b[1] < GRID_LENGTH):
            enemy_bullets.remove(b)

# ========================================================
# 11️⃣ INPUT, CAMERA & SETUP
# ========================================================
def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 4000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    if camera_mode == CAM_ORBIT:
        radius = 1200.0
        cam_z = 800.0 + camera_height_offset
        angle_rad = math.radians(camera_angle)
        cam_x = radius * math.cos(angle_rad)
        cam_y = radius * math.sin(angle_rad)
        gluLookAt(cam_x, cam_y, cam_z, 0, 0, 40, 0, 0, 1)
    
    elif camera_mode == CAM_TURRET_FOLLOW:
        angle_rad = math.radians(gun_angle)
        cam_x = player_x - 80.0 * math.cos(angle_rad)
        cam_y = player_y - 80.0 * math.sin(angle_rad)
        look_x = player_x + 100.0 * math.cos(angle_rad)
        look_y = player_y + 100.0 * math.sin(angle_rad)
        gluLookAt(cam_x, cam_y, 80.0 + camera_height_offset, look_x, look_y, 40.0, 0, 0, 1)
    
    elif camera_mode == CAM_FIRST_PERSON:
        angle_rad = math.radians(gun_angle)
        eye_x = player_x - 10 * math.cos(angle_rad)
        eye_y = player_y - 10 * math.sin(angle_rad)
        eye_z = 60.0 + camera_height_offset
        look_x = player_x + 100 * math.cos(angle_rad)
        look_y = player_y + 100 * math.sin(angle_rad)
        look_z = eye_z - 5
        gluLookAt(eye_x, eye_y, eye_z, look_x, look_y, look_z, 0, 0, 1)

def keyboardListener(key, x, y):
    global camera_mode, current_weapon, game_state, score, player_hp, difficulty
    global player_x, player_y, gun_angle
    
    if key == b' ':
        if game_state == GAME_PLAYING:
            game_state = GAME_PAUSED
        elif game_state == GAME_PAUSED:
            game_state = GAME_PLAYING
    
    if key == b'r' and (game_state == GAME_OVER or game_state == GAME_PAUSED):
        game_state = GAME_PLAYING
        score = 0
        player_hp = PLAYER_MAX_HP
        difficulty = 0
        player_x, player_y, gun_angle = 0.0, -150.0, 0.0
        enemies.clear()
        bullets.clear()
        enemy_bullets.clear()
        create_scenery()
        move_health_booster()
        initial_spawn()
        current_weapon = WEAPON_NORMAL
        camera_mode = CAM_TURRET_FOLLOW
    
    if game_state == GAME_PLAYING:
        if key == b'w':
            try_move_player('forward')
        if key == b's':
            try_move_player('backward')
        if key == b'a':
            try_rotate_gun('left')
        if key == b'd':
            try_rotate_gun('right')
    
    if key == b'1':
        current_weapon = WEAPON_NORMAL
    if key == b'2':
        current_weapon = WEAPON_LASER
    if key == b'3':
        current_weapon = WEAPON_BURST
    if key == b'4':
        current_weapon = WEAPON_SHOCKWAVE
    if key == b'q':
        camera_mode = (camera_mode + 1) % 3

def specialKeyListener(key, x, y):
    global camera_angle, camera_height_offset
    
    if key == GLUT_KEY_LEFT:
        camera_angle += 5
    if key == GLUT_KEY_RIGHT:
        camera_angle -= 5
    if key == GLUT_KEY_UP:
        camera_height_offset += 20
    if key == GLUT_KEY_DOWN:
        camera_height_offset -= 20
        if camera_height_offset < -55:
            camera_height_offset = -55

def mouseListener(button, state, x, y):
    if button == GLUT_LEFT_BUTTON:
        mouse_state[button] = state
    if state == GLUT_DOWN:
        shoot_weapon()

def idle():
    global enemy_pulse, fire_cooldown, burst_remaining
    
    if game_state == GAME_PLAYING:
        health_booster_pos['pulse'] += 0.1
        enemy_pulse += 0.12
        
        if fire_cooldown > 0:
            fire_cooldown -= 1
        
        if burst_remaining > 0 and fire_cooldown == 0:
            burst_remaining -= 1
            angle_rad = math.radians(gun_angle)
            start_x = player_x + math.cos(angle_rad) * GUN_LENGTH
            start_y = player_y + math.sin(angle_rad) * GUN_LENGTH
            bullets.append([start_x, start_y, 50.0, bullet_speed * math.cos(angle_rad), bullet_speed * math.sin(angle_rad), True, "burst"])
            if burst_remaining > 0:
                fire_cooldown = FIRE_CD_BURST
        
        update_game()
        update_bullets()
        update_enemy_bullets()
    
    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, 1000, 800)
    setupCamera()
    
    glEnable(GL_DEPTH_TEST)
    
    draw_environment()
    draw_health_booster()
    draw_turret()
    
    if laser_beam_active:
        glColor3f(1.0, 0.2, 0.2)
        glBegin(GL_LINES)
        angle_rad = math.radians(gun_angle)
        gun_tip_x = player_x + math.cos(angle_rad) * GUN_LENGTH
        gun_tip_y = player_y + math.sin(angle_rad) * GUN_LENGTH
        glVertex3f(gun_tip_x, gun_tip_y, 60)
        glVertex3f(laser_target_pos[0], laser_target_pos[1], laser_target_pos[2])
        glEnd()
    
    for e in enemies:
        draw_enemy(e, enemy_pulse)
    
    for b in bullets:
        draw_bullet(b)
    
    for b in enemy_bullets:
        draw_enemy_bullet(b)
    
    for e in enemies:
        draw_enemy_health_bar(e)
    
    glDisable(GL_DEPTH_TEST)
    draw_hud()
    
    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(50, 50)
    glutCreateWindow(b"Sentinel Siege: Template Edition")
    glClearColor(0.5, 0.8, 1.0, 1.0)
    
    create_scenery()
    move_health_booster()
    initial_spawn()
    
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    glutMainLoop()

if __name__ == "__main__":
    main()