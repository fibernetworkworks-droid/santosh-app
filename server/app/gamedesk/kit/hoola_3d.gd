extends Node
# Hoola3D - Hoola's own 3D gameplay kit (written by Hoola, never by the model; v2).
# One level of a small 3D game from proved pieces: a world with sky and sun, ground and blocks, a player who walks
# and jumps (keyboard AND touch), a follow / first-person camera, things to collect, enemies that patrol or chase,
# a goal, and a HUD with on-screen controls. Every piece is built in code, so it exports to the web as it is.
# v2 CHARACTERS: jointed people / robots / animals drawn in code (or her approved animated model) that walk, run, jump,
# attack, get hurt, fall down, wave and talk; a hero who can strike, foes with health, and people who speak.

const VERSION := 2

# ready-made looks for Hoola3D.look(name, changes): colours are "#RRGGBB"
const LOOKS := {
	"hero": {"shirt": "#FFB15C", "pants": "#2B3A67", "hair": "#2A1B12", "hair_style": "short"},
	"girl": {"shirt": "#E255A8", "pants": "#5B2A86", "hair": "#1E1410", "hair_style": "long", "outfit": "kurta", "height": 1.55},
	"boy": {"shirt": "#3FA7D6", "pants": "#30343F", "hair": "#1E1410", "hat": "cap", "hat_color": "#E2572B", "height": 1.3},
	"elder": {"shirt": "#F3EFE6", "pants": "#D9D2C0", "hair": "#DADADA", "hair_style": "bun", "outfit": "dress", "height": 1.5, "item": "staff"},
	"farmer": {"shirt": "#F2F0E6", "pants": "#C9B28A", "hat": "turban", "hat_color": "#E2572B", "hair_style": "none"},
	"guard": {"shirt": "#7A1F2B", "pants": "#2A2A33", "hat": "helmet", "hair_style": "none", "item": "sword", "build": "stocky"},
	"villain": {"shirt": "#2A1140", "pants": "#16081F", "skin": "#A9B89A", "hair_style": "none", "item": "sword", "height": 1.9, "build": "stocky", "eyes": "#FF3B3B"},
	"king": {"shirt": "#6B1FB5", "pants": "#3B0F6B", "hat": "crown", "outfit": "kurta", "hair": "#2A1B12"},
	"robot": {"style": "robot", "shirt": "#9AA7B8", "pants": "#5E6B7D", "skin": "#C9D3E0", "eyes": "#39E1FF", "hat": "antenna", "hair_style": "none"},
	"dog": {"kind": "animal", "shirt": "#B9824A", "skin": "#C99760", "height": 0.7},
	"cow": {"kind": "animal", "shirt": "#F4F1EA", "skin": "#F4F1EA", "height": 1.35, "build": "stocky", "horns": true},
}

signal coin_taken(total: int)
signal player_hit(hp: int)
signal player_fell
signal goal_reached
signal enemy_stomped(left: int)
signal enemy_defeated(left: int)          # a foe is gone, by a strike or by a stomp
signal npc_talked(who: String, line: int)  # she talked to a person: which line they said (0 = the first)

var player: CharacterBody3D = null
var cam: Camera3D = null
var hud: CanvasLayer = null
var coins := 0
var coins_total := 0
var enemies_left := 0
var playing := true            # false = the player and the enemies stand still (title / game over screens)

var _stick := Vector2.ZERO
var _stick_id := -1
var _stick_from := Vector2.ZERO
var _look := Vector2.ZERO
var _look_id := -1
var _jump := false
var act_on := false            # true once a hero can strike or a person can be talked to: the action button shows
var _act := false
var _foes: Array = []
var _npcs: Array = []

# ---------------------------------------------------------------- start / reset
func reset() -> void:
	# call before building a level again (restart): counters and touch state go back to zero
	player = null
	cam = null
	hud = null
	coins = 0
	coins_total = 0
	enemies_left = 0
	playing = true
	_stick = Vector2.ZERO
	_stick_id = -1
	_look = Vector2.ZERO
	_look_id = -1
	_jump = false
	act_on = false
	_act = false
	_foes.clear()
	_npcs.clear()

func mat(color: Color, glow: float = 0.0, rough: float = 0.85) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = rough
	if glow > 0.0:
		m.emission_enabled = true
		m.emission = color
		m.emission_energy_multiplier = glow
	return m

func paint(node: Node, key: String, tile_m: float = 2.0, fallback: Color = Color("#8A6B4A")) -> void:
	# one of her APPROVED textures (HoolaAssets) on a block / the ground, repeated every tile_m metres;
	# when there is no such texture the node simply gets the fallback colour
	var m := mat(fallback)
	var a := get_node_or_null("/root/HoolaAssets")
	if a != null and a.call("has", key):
		var t: Variant = a.call("tex", key)
		if t != null and t is Texture2D:
			m.albedo_color = Color.WHITE
			m.albedo_texture = t
			m.uv1_triplanar = true
			m.uv1_world_triplanar = true
			m.uv1_scale = Vector3.ONE / max(0.1, tile_m)
			m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	for c in node.get_children():
		if c is MeshInstance3D:
			(c as MeshInstance3D).material_override = m
	if node is MeshInstance3D:
		(node as MeshInstance3D).material_override = m

func _probe(key: String, value: Variant) -> void:
	var p := get_node_or_null("/root/HoolaProbe")
	if p != null:
		p.call("state", key, value)

func _probe_event(name: String) -> void:
	var p := get_node_or_null("/root/HoolaProbe")
	if p != null:
		p.call("event", name)

# ---------------------------------------------------------------- the world
func world(parent: Node, sky_top: Color = Color("#1B2A6B"), sky_horizon: Color = Color("#F2A65A"),
		sun: Color = Color("#FFF1D6")) -> Node3D:
	# sky + ambient light + a sun with shadows; returns the Node3D to put the level under
	var root := Node3D.new()
	root.name = "World"
	parent.add_child(root)
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = sky_top
	sky_mat.sky_horizon_color = sky_horizon
	sky_mat.ground_bottom_color = sky_top.darkened(0.6)
	sky_mat.ground_horizon_color = sky_horizon
	var sky := Sky.new()
	sky.sky_material = sky_mat
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.9
	var we := WorldEnvironment.new()
	we.environment = env
	root.add_child(we)
	var light := DirectionalLight3D.new()
	light.light_color = sun
	light.light_energy = 1.2
	light.shadow_enabled = true
	light.rotation_degrees = Vector3(-52.0, 35.0, 0.0)
	root.add_child(light)
	return root

func ground(parent: Node, size: Vector2 = Vector2(40.0, 40.0), color: Color = Color("#4E8B4A"),
		center: Vector3 = Vector3.ZERO) -> StaticBody3D:
	return block(parent, center + Vector3(0.0, -0.5, 0.0), Vector3(size.x, 1.0, size.y), color)

func block(parent: Node, pos: Vector3, size: Vector3, color: Color = Color("#8A6B4A"), solid: bool = true) -> StaticBody3D:
	# a wall, a floor or a platform: pos is its centre
	var body := StaticBody3D.new()
	body.position = pos
	var mesh := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mesh.mesh = bm
	mesh.material_override = mat(color)
	body.add_child(mesh)
	if solid:
		var cs := CollisionShape3D.new()
		var sh := BoxShape3D.new()
		sh.size = size
		cs.shape = sh
		body.add_child(cs)
	parent.add_child(body)
	return body

func moving_block(parent: Node, from: Vector3, to: Vector3, size: Vector3, color: Color = Color("#C98A4B"),
		seconds: float = 3.0) -> AnimatableBody3D:
	# a platform that carries the player between two points, for ever
	var body := AnimatableBody3D.new()
	body.position = from
	var mesh := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mesh.mesh = bm
	mesh.material_override = mat(color)
	body.add_child(mesh)
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = size
	cs.shape = sh
	body.add_child(cs)
	parent.add_child(body)
	var tw := body.create_tween().set_loops()
	tw.set_process_mode(Tween.TWEEN_PROCESS_PHYSICS)
	tw.tween_property(body, "position", to, max(0.3, seconds)).set_trans(Tween.TRANS_SINE)
	tw.tween_property(body, "position", from, max(0.3, seconds)).set_trans(Tween.TRANS_SINE)
	return body

func tree(parent: Node, pos: Vector3, height: float = 3.0, leaf: Color = Color("#2F7D4F")) -> Node3D:
	# decoration only (no collision): a trunk and a cone
	var n := Node3D.new()
	n.position = pos
	var trunk := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.18
	cm.bottom_radius = 0.24
	cm.height = height * 0.4
	trunk.mesh = cm
	trunk.material_override = mat(Color("#6B4A2E"))
	trunk.position.y = height * 0.2
	n.add_child(trunk)
	var top := MeshInstance3D.new()
	var cone := CylinderMesh.new()
	cone.top_radius = 0.0
	cone.bottom_radius = height * 0.32
	cone.height = height * 0.7
	top.mesh = cone
	top.material_override = mat(leaf)
	top.position.y = height * 0.4 + height * 0.35
	n.add_child(top)
	parent.add_child(n)
	return n

func model(parent: Node, key: String, pos: Vector3, size: float = 1.0) -> Node3D:
	# one of her APPROVED 3D models (HoolaAssets), or null when there is none: always keep a drawn fallback
	var a := get_node_or_null("/root/HoolaAssets")
	if a == null or not a.call("has", key):
		return null
	var ps: Variant = a.call("scene", key)
	if ps == null or not (ps is PackedScene):
		return null
	var inst: Node = (ps as PackedScene).instantiate()
	if not (inst is Node3D):
		inst.queue_free()
		return null
	var n3 := inst as Node3D
	n3.position = pos
	n3.scale = Vector3.ONE * size
	parent.add_child(n3)
	return n3

# ---------------------------------------------------------------- the player and the camera
func spawn_player(parent: Node, pos: Vector3, color: Color = Color("#FFB15C"), speed: float = 6.0,
		jump_height: float = 1.8, hp: int = 3) -> CharacterBody3D:
	var p := Player.new()
	p.kit = self
	p.speed = speed
	p.jump_height = jump_height
	p.hp = hp
	p.spawn = pos
	p.position = pos
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.4
	cap.height = 1.6
	cs.shape = cap
	cs.position.y = 0.8
	p.add_child(cs)
	var look := Node3D.new()
	look.name = "Look"
	p.add_child(look)
	p.look = look
	var body := MeshInstance3D.new()
	var cm := CapsuleMesh.new()
	cm.radius = 0.4
	cm.height = 1.6
	body.mesh = cm
	body.material_override = mat(color)
	body.position.y = 0.8
	look.add_child(body)
	var nose := MeshInstance3D.new()        # shows which way the player faces
	var nm := BoxMesh.new()
	nm.size = Vector3(0.5, 0.16, 0.2)
	nose.mesh = nm
	nose.material_override = mat(Color("#1B1030"))
	nose.position = Vector3(0.0, 1.25, -0.36)
	look.add_child(nose)
	parent.add_child(p)
	player = p
	_probe("hp", hp)
	return p

func follow_camera(target: Node3D, distance: float = 7.0, height: float = 0.5) -> Camera3D:
	# distance > 0 = third person behind the player; distance 0 = first person at eye height
	var c := FollowCam.new()
	c.kit = self
	c.target = target
	c.distance = max(0.0, distance)
	c.pitch = -0.38 - height * 0.05
	c.fov = 70.0
	c.current = true
	target.get_parent().add_child(c)
	c.snap()
	cam = c
	if c.distance <= 0.01 and target is Player:
		(target as Player).look.visible = false     # first person: the body is not drawn
	return c

func move_input() -> Vector2:
	# x = right, y = forward(-1) / back(+1): keyboard (arrows / WASD) plus the touch stick
	var v := _stick
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
		v.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
		v.x += 1.0
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
		v.y -= 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
		v.y += 1.0
	return v.limit_length(1.0)

func take_jump() -> bool:
	var j := _jump
	_jump = false
	return j

func take_act() -> bool:
	# the action key (F / J / X) or the on-screen action button: talk to the person nearby, else strike
	var a := _act
	_act = false
	return a

func take_look() -> Vector2:
	var l := _look
	_look = Vector2.ZERO
	return l

func _view() -> Vector2:
	return get_viewport().get_visible_rect().size

func jump_button() -> Rect2:
	var s := _view()
	var r: float = min(s.x, s.y) * 0.11
	return Rect2(s.x - r * 2.6, s.y - r * 2.6, r * 2.0, r * 2.0)

func act_button() -> Rect2:
	var s := _view()
	var r: float = min(s.x, s.y) * 0.11
	return Rect2(s.x - r * 4.9, s.y - r * 2.1, r * 1.7, r * 1.7)

func _input(event: InputEvent) -> void:
	if event is InputEventKey:
		var k := event as InputEventKey
		if k.pressed and not k.echo and (k.physical_keycode == KEY_SPACE or k.keycode == KEY_SPACE):
			_jump = true
		if k.pressed and not k.echo and (k.physical_keycode in [KEY_F, KEY_J, KEY_X] or k.keycode in [KEY_F, KEY_J, KEY_X]):
			_act = true
		return
	if event is InputEventScreenTouch:
		var t := event as InputEventScreenTouch
		if t.pressed:
			if jump_button().grow(12.0).has_point(t.position):
				_jump = true
			elif act_on and act_button().grow(10.0).has_point(t.position):
				_act = true
			elif t.position.x < _view().x * 0.5 and _stick_id == -1:
				_stick_id = t.index
				_stick_from = t.position
				_stick = Vector2.ZERO
			elif _look_id == -1:
				_look_id = t.index
		else:
			if t.index == _stick_id:
				_stick_id = -1
				_stick = Vector2.ZERO
			if t.index == _look_id:
				_look_id = -1
		_redraw_pad()
		return
	if event is InputEventScreenDrag:
		var d := event as InputEventScreenDrag
		if d.index == _stick_id:
			var r: float = min(_view().x, _view().y) * 0.13
			_stick = ((d.position - _stick_from) / r).limit_length(1.0)
			_redraw_pad()
		elif d.index == _look_id:
			_look += d.relative

func _redraw_pad() -> void:
	if hud != null and is_instance_valid(hud):
		(hud as Hud).pad.queue_redraw()

# ---------------------------------------------------------------- things in the level
func coin(parent: Node, pos: Vector3, color: Color = Color("#FFD23F"), value: int = 1) -> Area3D:
	var c := Coin.new()
	c.kit = self
	c.value = value
	c.position = pos
	var mesh := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.35
	cm.bottom_radius = 0.35
	cm.height = 0.08
	mesh.mesh = cm
	mesh.rotation_degrees.x = 90.0
	mesh.material_override = mat(color, 0.6, 0.3)
	c.add_child(mesh)
	var cs := CollisionShape3D.new()
	var sh := SphereShape3D.new()
	sh.radius = 0.6
	cs.shape = sh
	c.add_child(cs)
	parent.add_child(c)
	coins_total += value
	return c

func enemy(parent: Node, pos: Vector3, patrol_to: Vector3 = Vector3.ZERO, speed: float = 2.5,
		chase_range: float = 0.0, color: Color = Color("#D9466F")) -> Area3D:
	# walks between pos and patrol_to (leave ZERO to stand guard); chase_range > 0 = runs at the player when near.
	# Touching it costs 1 hp; landing on it from above removes it.
	var e := Enemy.new()
	e.kit = self
	e.a = pos
	e.b = pos if patrol_to == Vector3.ZERO else patrol_to
	e.speed = speed
	e.chase_range = chase_range
	e.position = pos
	var mesh := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.55
	sm.height = 1.0
	mesh.mesh = sm
	mesh.material_override = mat(color)
	mesh.position.y = 0.5
	e.add_child(mesh)
	for side in [-1.0, 1.0]:
		var eye := MeshInstance3D.new()
		var em := SphereMesh.new()
		em.radius = 0.1
		em.height = 0.2
		eye.mesh = em
		eye.material_override = mat(Color.WHITE, 0.4)
		eye.position = Vector3(0.2 * side, 0.65, -0.45)
		mesh.add_child(eye)
	var cs := CollisionShape3D.new()
	var sh := SphereShape3D.new()
	sh.radius = 0.6
	cs.shape = sh
	cs.position.y = 0.5
	e.add_child(cs)
	parent.add_child(e)
	enemies_left += 1
	_foes.append(e)
	return e

func goal(parent: Node, pos: Vector3, color: Color = Color("#46D68C")) -> Area3D:
	var g := Goal.new()
	g.kit = self
	g.position = pos
	var mesh := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.9
	cm.bottom_radius = 0.9
	cm.height = 3.0
	mesh.mesh = cm
	var m := mat(color, 1.6, 0.2)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color.a = 0.55
	mesh.material_override = m
	mesh.position.y = 1.5
	g.add_child(mesh)
	var lamp := OmniLight3D.new()
	lamp.light_color = color
	lamp.light_energy = 2.0
	lamp.omni_range = 7.0
	lamp.position.y = 2.0
	g.add_child(lamp)
	var cs := CollisionShape3D.new()
	var sh := CylinderShape3D.new()
	sh.radius = 0.9
	sh.height = 3.0
	cs.shape = sh
	cs.position.y = 1.5
	g.add_child(cs)
	parent.add_child(g)
	return g

# ---------------------------------------------------------------- characters (v2)
func look(preset: String, changes: Dictionary = {}) -> Dictionary:
	# a ready-made look ("hero", "girl", "boy", "elder", "farmer", "guard", "villain", "king", "robot", "dog", "cow")
	# with your changes on top: Hoola3D.look("guard", {"shirt": "#1F4E7A", "height": 1.9})
	var s: Dictionary = (LOOKS.get(preset, LOOKS["hero"]) as Dictionary).duplicate()
	for k in changes:
		s[k] = changes[k]
	return s

func _col(s: Dictionary, key: String, d: String) -> Color:
	var v: Variant = s.get(key, d)
	if v is Color:
		return v
	return Color.from_string(str(v), Color.from_string(d, Color.WHITE))

func _part(parent: Node3D, mesh: Mesh, m: Material, pos: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = m
	mi.position = pos
	parent.add_child(mi)
	return mi

func _pivot(f: Figure, parent: Node3D, key: String, pos: Vector3) -> Node3D:
	var n := Node3D.new()
	n.name = key
	n.position = pos
	parent.add_child(n)
	f.j[key] = n
	return n

func _limb(length: float, r: float, boxy: bool) -> Mesh:
	if boxy:
		var b := BoxMesh.new()
		b.size = Vector3(r * 2.0, length, r * 2.0)
		return b
	var c := CapsuleMesh.new()
	c.radius = r
	c.height = max(length + r, r * 2.0)
	return c

func _ball(r: float, squash: float = 1.0) -> SphereMesh:
	var sm := SphereMesh.new()
	sm.radius = r
	sm.height = r * 2.0 * squash
	return sm

func _box(size: Vector3) -> BoxMesh:
	var b := BoxMesh.new()
	b.size = size
	return b

func _tube(top: float, bottom: float, height: float) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = top
	c.bottom_radius = bottom
	c.height = height
	return c

func figure(parent: Node, pos: Vector3, spec: Dictionary = {}) -> Node3D:
	# a character that only stands there (decoration / your own logic): drive it with .set_motion(0..1) and .play(name)
	var f := _make_figure(spec)
	f.position = pos
	parent.add_child(f)
	return f

func figure_from(parent: Node, pos: Vector3, scene_root: Node3D, spec: Dictionary = {}) -> Node3D:
	# the same, from a 3D model you already instantiated (its own idle / walk / run / jump clips are found by name)
	var f := Figure.new()
	f.kit = self
	f.height = clamp(float(spec.get("height", 1.7)), 0.3, 4.0)
	_wrap_model(f, scene_root, spec)
	f.position = pos
	parent.add_child(f)
	return f

func _make_figure(spec: Dictionary) -> Figure:
	var f := Figure.new()
	f.kit = self
	f.height = clamp(float(spec.get("height", 1.7)), 0.3, 4.0)
	if spec.has("model"):
		var a := get_node_or_null("/root/HoolaAssets")
		if a != null and a.call("has", str(spec["model"])):
			var ps: Variant = a.call("scene", str(spec["model"]))
			if ps != null and ps is PackedScene:
				var inst: Node = (ps as PackedScene).instantiate()
				if inst is Node3D:
					_wrap_model(f, inst as Node3D, spec)
					return f
				inst.queue_free()
	if str(spec.get("kind", "")) == "animal":
		_build_quad(f, spec)
	else:
		_build_biped(f, spec)
	return f

func _bounds(n: Node, xf: Transform3D, acc: Array) -> void:
	if n is VisualInstance3D:
		acc.append(xf * (n as VisualInstance3D).get_aabb())
	for c in n.get_children():
		if c is Node3D:
			_bounds(c, xf * (c as Node3D).transform, acc)
		else:
			_bounds(c, xf, acc)

func _wrap_model(f: Figure, inst: Node3D, spec: Dictionary) -> void:
	var body := Node3D.new()
	body.name = "Body"
	f.add_child(body)
	f.body = body
	body.add_child(inst)
	inst.transform = Transform3D.IDENTITY
	var acc: Array = []
	_bounds(inst, Transform3D.IDENTITY, acc)
	if acc.size() > 0:
		var box: AABB = acc[0]
		for b in acc:
			box = box.merge(b)
		if box.size.y > 0.001:
			var k: float = f.height / box.size.y
			inst.scale = Vector3.ONE * k
			inst.position.y = -box.position.y * k
	inst.rotation_degrees.y = float(spec.get("model_turn", 180.0))     # most models face +Z; the kit walks towards -Z
	var players := inst.find_children("*", "AnimationPlayer", true, false)
	if players.size() > 0:
		f.ap = players[0] as AnimationPlayer
		var words := {"hurt": ["hurt", "damage", "pain"], "die": ["die", "death", "dead"], "idle": ["idle", "stand", "breath"],
			"walk": ["walk"], "run": ["run", "sprint", "jog"], "jump": ["jump"], "fall": ["fall"],
			"attack": ["attack", "punch", "slash", "kick", "shoot", "hit"], "wave": ["wave", "hello"], "talk": ["talk"]}
		for clip in f.ap.get_animation_list():
			var low := str(clip).to_lower()
			for st in words:
				if f.clips.has(st):
					continue
				for w in words[st]:
					if low.contains(w):
						f.clips[st] = str(clip)
						break
		for st in ["idle", "walk", "run"]:
			if f.clips.has(st):
				f.ap.get_animation(f.clips[st]).loop_mode = Animation.LOOP_LINEAR

func _build_biped(f: Figure, s: Dictionary) -> void:
	var h: float = f.height
	var boxy := str(s.get("style", "")) == "robot"
	var wide: float = float({"slim": 0.82, "stocky": 1.25}.get(str(s.get("build", "normal")), 1.0))
	var skin := mat(_col(s, "skin", "#C68A5E"), 0.0, 0.3 if boxy else 0.8)
	var shirt := mat(_col(s, "shirt", "#FFB15C"), 0.0, 0.35 if boxy else 0.85)
	var pants := mat(_col(s, "pants", "#2B3A67"), 0.0, 0.35 if boxy else 0.85)
	var shoes := mat(_col(s, "shoes", "#1B1030"))
	var hair := mat(_col(s, "hair", "#2A1B12"))
	var leg := 0.46 * h
	var th := leg * 0.5
	var torso_h := 0.32 * h
	var head_r := 0.088 * h
	var sw := 0.115 * h * wide
	var hw := 0.06 * h * wide
	var lr := 0.042 * h * wide
	var ua := 0.16 * h
	var fa := 0.15 * h
	var body := Node3D.new()
	body.name = "Body"
	f.add_child(body)
	f.body = body
	var hips := _pivot(f, body, "hips", Vector3(0.0, leg, 0.0))
	f.hips_y = leg
	var torso := _pivot(f, hips, "torso", Vector3.ZERO)
	if boxy:
		_part(torso, _box(Vector3(sw * 2.0, torso_h, 0.15 * h * wide)), shirt, Vector3(0.0, torso_h * 0.5, 0.0))
	else:
		var tm := _part(torso, _limb(torso_h * 0.75, sw * 0.82, false), shirt, Vector3(0.0, torso_h * 0.5, 0.0))
		tm.scale = Vector3(1.0, 1.0, 0.68)
	var outfit := str(s.get("outfit", ""))
	if outfit == "kurta":
		_part(hips, _tube(sw * 0.8, sw * 1.12, 0.17 * h), shirt, Vector3(0.0, -0.06 * h, 0.0)).scale = Vector3(1.0, 1.0, 0.72)
	elif outfit == "dress":
		_part(hips, _tube(sw * 0.8, sw * 1.45, 0.38 * h), shirt, Vector3(0.0, -0.17 * h, 0.0)).scale = Vector3(1.0, 1.0, 0.8)
	var head := _pivot(f, torso, "head", Vector3(0.0, torso_h + 0.02 * h, 0.0))
	if boxy:
		_part(head, _box(Vector3(head_r * 2.2, head_r * 1.9, head_r * 2.0)), skin, Vector3(0.0, head_r, 0.0))
	else:
		_part(head, _ball(head_r), skin, Vector3(0.0, head_r, 0.0))
	var eye_m := mat(_col(s, "eyes", "#1B1030"), 2.0 if (boxy or s.has("eyes")) else 0.0, 0.3)
	for side in [-1.0, 1.0]:
		_part(head, _ball(head_r * 0.17), eye_m, Vector3(head_r * 0.38 * side, head_r * 1.02, -head_r * (1.08 if boxy else 0.93)))
	var style := str(s.get("hair_style", "short"))
	if style != "none" and not boxy:
		_part(head, _ball(head_r * 1.07, 0.74), hair, Vector3(0.0, head_r * 1.34, head_r * 0.2))
		if style == "long":
			_part(head, _box(Vector3(head_r * 1.75, head_r * 2.3, head_r * 0.55)), hair, Vector3(0.0, head_r * 0.45, head_r * 0.82))
		elif style == "bun":
			_part(head, _ball(head_r * 0.42), hair, Vector3(0.0, head_r * 2.05, head_r * 0.45))
	var hat := str(s.get("hat", ""))
	var hat_m := mat(_col(s, "hat_color", "#E2572B"))
	if hat == "cap":
		_part(head, _tube(head_r * 0.95, head_r * 1.1, head_r * 0.55), hat_m, Vector3(0.0, head_r * 1.78, 0.0))
		_part(head, _box(Vector3(head_r * 1.5, head_r * 0.1, head_r * 0.9)), hat_m, Vector3(0.0, head_r * 1.55, -head_r * 1.25))
	elif hat == "turban":
		_part(head, _ball(head_r * 1.28, 0.62), hat_m, Vector3(0.0, head_r * 1.82, 0.0))
		_part(head, _ball(head_r * 0.34), hat_m, Vector3(head_r * 0.2, head_r * 2.5, 0.0))
	elif hat == "crown":
		_part(head, _tube(head_r * 1.0, head_r * 0.8, head_r * 0.62), mat(Color("#FFD23F"), 0.7, 0.25), Vector3(0.0, head_r * 2.05, 0.0))
	elif hat == "helmet":
		_part(head, _ball(head_r * 1.16, 0.6), mat(_col(s, "hat_color", "#8D97A6"), 0.0, 0.3), Vector3(0.0, head_r * 1.72, 0.0))
		_part(head, _tube(head_r * 0.1, head_r * 0.1, head_r * 0.7), mat(Color("#D9466F")), Vector3(0.0, head_r * 2.55, 0.0))
	elif hat == "antenna":
		_part(head, _tube(head_r * 0.07, head_r * 0.07, head_r * 0.9), shoes, Vector3(0.0, head_r * 2.35, 0.0))
		_part(head, _ball(head_r * 0.2), eye_m, Vector3(0.0, head_r * 2.85, 0.0))
	for side in [-1.0, 1.0]:
		var tag := "l" if side < 0.0 else "r"
		var arm := _pivot(f, torso, "arm_" + tag, Vector3(side * (sw + lr * 0.55), torso_h * 0.9, 0.0))
		_part(arm, _limb(ua, lr * 0.9, boxy), shirt, Vector3(0.0, -ua * 0.5, 0.0))
		var elbow := _pivot(f, arm, "elbow_" + tag, Vector3(0.0, -ua, 0.0))
		_part(elbow, _limb(fa, lr * 0.8, boxy), shirt if boxy else skin, Vector3(0.0, -fa * 0.5, 0.0))
		_part(elbow, _ball(lr * 1.0), skin, Vector3(0.0, -fa, 0.0))
		if side > 0.0:
			var hand := _pivot(f, elbow, "hand_r", Vector3(0.0, -fa, 0.0))
			var item := str(s.get("item", ""))
			if item == "sword":
				_part(hand, _box(Vector3(0.02 * h, 0.05 * h, 0.42 * h)), mat(Color("#DDE3EC"), 0.25, 0.2), Vector3(0.0, 0.0, -0.24 * h))
				_part(hand, _box(Vector3(0.13 * h, 0.03 * h, 0.03 * h)), mat(Color("#8A6B4A")), Vector3(0.0, 0.0, -0.03 * h))
			elif item == "staff":
				_part(hand, _tube(0.014 * h, 0.016 * h, 0.9 * h), mat(Color("#6B4A2E")), Vector3(0.0, 0.01 * h, -0.02 * h))
			elif item == "lamp":
				_part(hand, _ball(0.045 * h), mat(Color("#FFD23F"), 2.2, 0.3), Vector3(0.0, -0.06 * h, 0.0))
		var hip := _pivot(f, hips, "leg_" + tag, Vector3(side * hw, 0.0, 0.0))
		_part(hip, _limb(th, lr * 1.12, boxy), pants, Vector3(0.0, -th * 0.5, 0.0))
		var knee := _pivot(f, hip, "knee_" + tag, Vector3(0.0, -th, 0.0))
		_part(knee, _limb(th * 0.9, lr * 0.98, boxy), pants, Vector3(0.0, -th * 0.5, 0.0))
		_part(knee, _box(Vector3(lr * 2.3, 0.04 * h, 0.115 * h)), shoes, Vector3(0.0, -th + 0.02 * h, -0.03 * h))

func _build_quad(f: Figure, s: Dictionary) -> void:
	var h: float = f.height
	f.quad = true
	var wide: float = float({"slim": 0.82, "stocky": 1.2}.get(str(s.get("build", "normal")), 1.0))
	var coat := mat(_col(s, "shirt", "#B9824A"))
	var face := mat(_col(s, "skin", "#C99760"))
	var dark := mat(Color("#1B1030"))
	var br := 0.2 * h * wide
	var bl := 1.05 * h
	var ll := 0.42 * h
	var body := Node3D.new()
	body.name = "Body"
	f.add_child(body)
	f.body = body
	var hips := _pivot(f, body, "hips", Vector3(0.0, ll + br, 0.0))
	f.hips_y = ll + br
	var torso := _pivot(f, hips, "torso", Vector3.ZERO)
	var tm := _part(torso, _limb(bl - br * 2.0, br, false), coat)
	tm.rotation_degrees.x = 90.0
	var head := _pivot(f, torso, "head", Vector3(0.0, br * 0.55, -bl * 0.5 + br * 0.4))
	var hr := 0.15 * h
	_part(head, _ball(hr), face, Vector3(0.0, hr * 0.7, -hr * 0.7))
	_part(head, _box(Vector3(hr * 0.9, hr * 0.7, hr * 0.9)), face, Vector3(0.0, hr * 0.35, -hr * 1.65))
	_part(head, _ball(hr * 0.2), dark, Vector3(0.0, hr * 0.55, -hr * 2.1))
	for side in [-1.0, 1.0]:
		_part(head, _ball(hr * 0.13), dark, Vector3(hr * 0.45 * side, hr * 1.0, -hr * 1.45))
		_part(head, _box(Vector3(hr * 0.4, hr * 0.7, hr * 0.14)), coat, Vector3(hr * 0.75 * side, hr * 1.5, -hr * 0.55))
		if bool(s.get("horns", false)):
			_part(head, _tube(0.0, hr * 0.13, hr * 0.8), mat(Color("#EDE6D6")), Vector3(hr * 0.5 * side, hr * 1.95, -hr * 0.7))
	var tail := _pivot(f, torso, "tail", Vector3(0.0, br * 0.5, bl * 0.5 - br * 0.3))
	var tl := _part(tail, _tube(br * 0.1, br * 0.16, 0.34 * h), coat, Vector3(0.0, 0.08 * h, 0.1 * h))
	tl.rotation_degrees.x = 50.0
	for fb in [-1.0, 1.0]:
		for side in [-1.0, 1.0]:
			var key := "leg_" + ("f" if fb < 0.0 else "b") + ("l" if side < 0.0 else "r")
			var lg := _pivot(f, hips, key, Vector3(side * br * 0.62, -br * 0.4, fb * (bl * 0.5 - br * 1.1)))
			var ln := ll + br * 0.4
			_part(lg, _limb(ln - br * 0.3, br * 0.3, false), coat, Vector3(0.0, -ln * 0.5, 0.0))

func spawn_hero(parent: Node, pos: Vector3, spec: Dictionary = {}, speed: float = 6.0, jump_height: float = 1.8,
		hp: int = 3) -> CharacterBody3D:
	# spawn_player with a real character for a body. spec = Hoola3D.look("hero", {...}); a hero holding a sword
	# (or with "attack": true) strikes with the action key F / J / X or the on-screen action button.
	var s := look("hero", spec)
	var p := Player.new()
	p.kit = self
	p.speed = speed
	p.jump_height = jump_height
	p.hp = hp
	p.spawn = pos
	p.position = pos
	var f := _make_figure(s)
	var tall: float = clamp(f.height, 0.8, 2.4)
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = min(0.4, tall * 0.25)
	cap.height = tall
	cs.shape = cap
	cs.position.y = tall * 0.5
	p.add_child(cs)
	var lk := Node3D.new()
	lk.name = "Look"
	p.add_child(lk)
	p.look = lk
	lk.add_child(f)
	p.figure = f
	p.can_attack = bool(s.get("attack", str(s.get("item", "")) == "sword"))
	p.attack_power = max(1, int(s.get("power", 1)))
	f.strike.connect(_strike)
	if p.can_attack:
		act_on = true
	parent.add_child(p)
	player = p
	_probe("hp", hp)
	return p

func foe(parent: Node, pos: Vector3, spec: Dictionary = {}, patrol_to: Vector3 = Vector3.ZERO, speed: float = 2.5,
		chase_range: float = 0.0, hp: int = 2) -> Area3D:
	# enemy() with a real character for a body and health: each strike of the hero takes 1 (it staggers, then falls);
	# its touch costs the player 1 hp; landing on it still removes it at once.
	var s := look("guard", spec)
	var e := Enemy.new()
	e.kit = self
	e.a = pos
	e.b = pos if patrol_to == Vector3.ZERO else patrol_to
	e.speed = speed
	e.chase_range = chase_range
	e.hp = max(1, hp)
	e.position = pos
	var f := _make_figure(s)
	e.add_child(f)
	e.figure = f
	var cs := CollisionShape3D.new()
	if f.quad:
		var sp := SphereShape3D.new()
		sp.radius = max(0.45, f.height * 0.5)
		cs.shape = sp
		cs.position.y = f.height * 0.5
	else:
		var cap := CapsuleShape3D.new()
		cap.radius = 0.5
		cap.height = max(1.0, f.height)
		cs.shape = cap
		cs.position.y = max(1.0, f.height) * 0.5
	e.add_child(cs)
	parent.add_child(e)
	enemies_left += 1
	_foes.append(e)
	return e

func npc(parent: Node, pos: Vector3, who: String, lines: Array = [], spec: Dictionary = {}, talk_range: float = 2.6) -> Node3D:
	# a person who stands there, turns to the player, waves when the player comes near and says the next of `lines`
	# each time the player presses the action key / button beside them (the last line repeats). npc_talked(who, index)
	# fires each time - use it for quests ("talk to Dadi first").
	var n := Npc.new()
	n.kit = self
	n.who = who
	n.lines = lines
	n.talk_range = talk_range
	n.position = pos
	var f := _make_figure(look("elder", spec) if spec.is_empty() else spec)
	n.add_child(f)
	n.figure = f
	var tag := Label3D.new()
	tag.text = who
	tag.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	tag.font_size = 44
	tag.outline_size = 10
	tag.pixel_size = 0.006
	tag.position.y = f.height + 0.35
	n.add_child(tag)
	var hint := Label3D.new()
	hint.text = "..."
	hint.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	hint.font_size = 64
	hint.outline_size = 12
	hint.pixel_size = 0.006
	hint.modulate = Color("#FFD23F")
	hint.position.y = f.height + 0.7
	hint.visible = false
	n.add_child(hint)
	n.hint = hint
	parent.add_child(n)
	_npcs.append(n)
	act_on = true
	return n

# ---------------------------------------------------------------- what happens to the player
func _took(c: Area3D, value: int) -> void:
	coins += value
	c.queue_free()
	_probe("score", coins)
	if hud != null and is_instance_valid(hud):
		(hud as Hud).set_score("%d / %d" % [coins, coins_total])
	coin_taken.emit(coins)

func hurt(amount: int = 1, from: Vector3 = Vector3.ZERO) -> void:
	if player == null or not is_instance_valid(player):
		return
	var p := player as Player
	if p.invulnerable > 0.0 or not playing:
		return
	p.hp = max(0, p.hp - amount)
	p.invulnerable = 1.2
	var away := p.global_position - from
	away.y = 0.0
	if away.length() > 0.01:
		p.velocity = away.normalized() * 6.0 + Vector3(0.0, 4.0, 0.0)
	_probe("hp", p.hp)
	if hud != null and is_instance_valid(hud):
		(hud as Hud).set_hp(p.hp)
	player_hit.emit(p.hp)

func _fell() -> void:
	var p := player as Player
	p.global_position = p.spawn + Vector3(0.0, 0.5, 0.0)
	p.velocity = Vector3.ZERO
	p.invulnerable = 0.0
	player_fell.emit()
	hurt(1)

func _reached() -> void:
	# fires every time the player walks into the goal: the game decides whether that is a win yet
	goal_reached.emit()

func _stomped(e: Area3D) -> void:
	_defeated(e, true)

func _defeated(e: Area3D, stomped: bool) -> void:
	var en := e as Enemy
	if en.dead:
		return
	en.dead = true
	_foes.erase(e)
	enemies_left = max(0, enemies_left - 1)
	_probe("enemies", enemies_left)
	e.set_deferred("monitoring", false)
	if en.figure != null and is_instance_valid(en.figure):
		en.figure.play("die")           # it falls down, then goes
		en._gone = 1.2
	else:
		e.queue_free()
	if stomped:
		if player != null and is_instance_valid(player):
			player.velocity.y = 7.0
		enemy_stomped.emit(enemies_left)
	enemy_defeated.emit(enemies_left)

func _strike() -> void:
	# the hero's blow lands: every foe close enough and in front loses health
	if player == null or not is_instance_valid(player) or not playing:
		return
	var p := player as Player
	var fwd := -p.look.global_transform.basis.z
	for e in _foes.duplicate():
		if not is_instance_valid(e) or (e as Enemy).dead:
			continue
		var d: Vector3 = (e as Node3D).global_position - p.global_position
		var dy := absf(d.y)
		d.y = 0.0
		if dy < 2.0 and d.length() <= p.attack_range and (d.length() < 0.8 or fwd.dot(d.normalized()) > 0.25):
			(e as Enemy).take_hit(p.attack_power, p.global_position)

func _try_talk() -> bool:
	if player == null or not is_instance_valid(player):
		return false
	var best: Npc = null
	var best_d := 1e9
	for n in _npcs:
		if not is_instance_valid(n):
			continue
		var d: float = ((n as Node3D).global_position - player.global_position).length()
		if d <= (n as Npc).talk_range and d < best_d:
			best = n as Npc
			best_d = d
	if best == null:
		return false
	best.talk()
	return true

func _said(who: String, line: String, index: int) -> void:
	if hud != null and is_instance_valid(hud):
		(hud as Hud).say(who, line)
	_probe("talked", who)
	_probe_event("talk")
	npc_talked.emit(who, index)

# ---------------------------------------------------------------- the HUD (score, lives, messages, touch controls)
func make_hud(parent: Node) -> CanvasLayer:
	var h := Hud.new()
	h.kit = self
	parent.add_child(h)
	hud = h
	h.set_score("0 / %d" % coins_total)
	if player != null and is_instance_valid(player):
		h.set_hp((player as Player).hp)
	return h


class Player extends CharacterBody3D:
	var kit: Node
	var look: Node3D
	var speed := 6.0
	var jump_height := 1.8
	var hp := 3
	var spawn := Vector3.ZERO
	var fall_y := -14.0
	var invulnerable := 0.0
	var figure: Node3D = null          # spawn_hero: the character that is this player's body
	var can_attack := false
	var attack_range := 2.2
	var attack_power := 1
	var _cool := 0.0

	func _physics_process(delta: float) -> void:
		var g: float = float(ProjectSettings.get_setting("physics/3d/default_gravity"))
		if not is_on_floor():
			velocity.y -= g * delta
		if invulnerable > 0.0:
			invulnerable -= delta
			look.visible = (kit.cam == null or kit.cam.distance > 0.01) and int(invulnerable * 12.0) % 2 == 0
			if invulnerable <= 0.0:
				look.visible = kit.cam == null or kit.cam.distance > 0.01
		var dir := Vector2.ZERO
		if kit.playing:
			dir = kit.move_input()
			if kit.take_jump() and is_on_floor():
				velocity.y = sqrt(2.0 * g * jump_height)
		var yaw := 0.0
		if kit.cam != null and is_instance_valid(kit.cam):
			yaw = kit.cam.yaw
		var v := Vector3(dir.x, 0.0, dir.y).rotated(Vector3.UP, yaw) * speed
		if invulnerable > 0.9:
			v = Vector3(velocity.x, 0.0, velocity.z)        # the knock-back plays out first
		velocity.x = v.x
		velocity.z = v.z
		if Vector2(v.x, v.z).length() > 0.2:
			look.rotation.y = lerp_angle(look.rotation.y, atan2(-v.x, -v.z), min(1.0, delta * 12.0))
		move_and_slide()
		if figure != null:
			figure.set_motion(Vector2(velocity.x, velocity.z).length() / max(0.1, speed), is_on_floor(), velocity.y)
		_cool -= delta
		if kit.playing and kit.take_act():
			if not kit._try_talk() and can_attack and _cool <= 0.0:
				_cool = 0.5
				if figure != null:
					figure.play("attack")
				else:
					kit._strike()
		if global_position.y < fall_y:
			kit._fell()


class FollowCam extends Camera3D:
	var kit: Node
	var target: Node3D
	var distance := 7.0
	var yaw := 0.0
	var pitch := -0.4

	func _want() -> Vector3:
		var t := target.global_position + Vector3(0.0, 1.3, 0.0)
		if distance <= 0.01:
			return t + Vector3(0.0, 0.3, 0.0)
		return t + Vector3(0.0, 0.0, distance).rotated(Vector3.RIGHT, pitch).rotated(Vector3.UP, yaw)

	func snap() -> void:
		global_position = _want()
		_aim()

	func _aim() -> void:
		if distance <= 0.01:
			rotation = Vector3(pitch, yaw, 0.0)
		else:
			look_at(target.global_position + Vector3(0.0, 1.3, 0.0), Vector3.UP)

	func _process(delta: float) -> void:
		if target == null or not is_instance_valid(target):
			return
		var l: Vector2 = kit.take_look()
		yaw -= l.x * 0.006
		pitch = clamp(pitch - l.y * 0.005, -1.2, 0.35)
		if Input.is_physical_key_pressed(KEY_Q):
			yaw += delta * 1.8
		if Input.is_physical_key_pressed(KEY_E):
			yaw -= delta * 1.8
		global_position = global_position.lerp(_want(), min(1.0, delta * 9.0)) if distance > 0.01 else _want()
		_aim()


class Coin extends Area3D:
	var kit: Node
	var value := 1

	func _ready() -> void:
		body_entered.connect(_on_body)

	func _process(delta: float) -> void:
		rotation.y += delta * 3.0

	func _on_body(body: Node) -> void:
		if body == kit.player:
			kit._took(self, value)


class Enemy extends Area3D:
	var kit: Node
	var a := Vector3.ZERO
	var b := Vector3.ZERO
	var speed := 2.5
	var chase_range := 0.0
	var _to_b := true
	var hp := 1
	var dead := false
	var figure: Node3D = null          # foe(): the character that is this enemy's body
	var _stun := 0.0
	var _gone := 0.0

	func _ready() -> void:
		body_entered.connect(_on_body)

	func take_hit(amount: int, from: Vector3) -> void:
		if dead:
			return
		hp -= amount
		if hp <= 0:
			kit._defeated(self, false)
			return
		_stun = 0.45
		var away := global_position - from
		away.y = 0.0
		if away.length() > 0.01:
			global_position += away.normalized() * 0.6
		if figure != null:
			figure.play("hurt")

	func _physics_process(delta: float) -> void:
		if dead:
			_gone -= delta
			if _gone <= 0.0:
				queue_free()
			return
		if not kit.playing:
			if figure != null:
				figure.set_motion(0.0)
			return
		if _stun > 0.0:
			_stun -= delta
			return
		var goal_pos := b if _to_b else a
		var p: Node3D = kit.player
		if chase_range > 0.0 and p != null and is_instance_valid(p):
			var flat := p.global_position - global_position
			flat.y = 0.0
			if flat.length() <= chase_range:
				goal_pos = Vector3(p.global_position.x, global_position.y, p.global_position.z)
		var step := goal_pos - global_position
		step.y = 0.0
		if step.length() < 0.15:
			_to_b = not _to_b
			if figure != null:
				figure.set_motion(0.0)
			return
		var move := step.normalized() * speed * delta
		global_position += move
		rotation.y = lerp_angle(rotation.y, atan2(-move.x, -move.z), min(1.0, delta * 8.0))
		if figure != null:
			figure.set_motion(clamp(speed / 4.5, 0.25, 1.0))

	func _on_body(body: Node) -> void:
		if body != kit.player or not kit.playing or dead:
			return
		var p := body as CharacterBody3D
		if p.velocity.y < -1.0 and p.global_position.y > global_position.y + 0.35:
			kit._stomped(self)
		else:
			if figure != null:
				figure.play("attack")
			kit.hurt(1, global_position)


class Goal extends Area3D:
	var kit: Node

	func _ready() -> void:
		body_entered.connect(_on_body)

	func _on_body(body: Node) -> void:
		if body == kit.player and kit.playing:
			kit._reached()


class Pad extends Control:
	var kit: Node

	func _draw() -> void:
		var s := get_viewport_rect().size
		var r: float = min(s.x, s.y) * 0.13
		var c := Vector2(r * 1.6, s.y - r * 1.6)
		if kit._stick_id != -1:
			c = kit._stick_from
		draw_circle(c, r, Color(1, 1, 1, 0.10))
		draw_arc(c, r, 0.0, TAU, 48, Color(1, 1, 1, 0.35), 3.0)
		draw_circle(c + kit._stick * r * 0.7, r * 0.42, Color(1, 1, 1, 0.45))
		var jb: Rect2 = kit.jump_button()
		draw_circle(jb.get_center(), jb.size.x * 0.5, Color(1, 0.69, 0.36, 0.30))
		draw_arc(jb.get_center(), jb.size.x * 0.5, 0.0, TAU, 48, Color(1, 0.69, 0.36, 0.8), 3.0)
		if kit.act_on:
			var ab: Rect2 = kit.act_button()
			draw_circle(ab.get_center(), ab.size.x * 0.5, Color(0.55, 0.48, 1.0, 0.30))
			draw_arc(ab.get_center(), ab.size.x * 0.5, 0.0, TAU, 48, Color(0.55, 0.48, 1.0, 0.85), 3.0)


class Hud extends CanvasLayer:
	var kit: Node
	var score: Label
	var lives: Label
	var title: Label
	var sub: Label
	var shade: ColorRect
	var pad: Control
	var talk: Label
	var talk_bg: ColorRect
	var _say := 0.0

	func _label(size: int, color: Color) -> Label:
		var l := Label.new()
		l.add_theme_font_size_override("font_size", size)
		l.add_theme_color_override("font_color", color)
		l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.7))
		l.add_theme_constant_override("outline_size", 6)
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(l)
		return l

	func _ready() -> void:
		var s := get_viewport().get_visible_rect().size
		var big: int = int(min(s.x, s.y) * 0.09)
		shade = ColorRect.new()
		shade.color = Color(0.04, 0.04, 0.07, 0.62)
		shade.set_anchors_preset(Control.PRESET_FULL_RECT)
		shade.size = s
		shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
		shade.visible = false
		add_child(shade)
		pad = Pad.new()
		(pad as Pad).kit = kit
		pad.set_anchors_preset(Control.PRESET_FULL_RECT)
		pad.size = s
		pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(pad)
		score = _label(int(big * 0.5), Color("#FFD23F"))
		score.position = Vector2(24, 18)
		lives = _label(int(big * 0.5), Color("#FF7A7A"))
		lives.position = Vector2(s.x - big * 3.2, 18)
		title = _label(big, Color.WHITE)
		title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		title.size = Vector2(s.x, big * 1.4)
		title.position = Vector2(0, s.y * 0.34)
		sub = _label(int(big * 0.42), Color("#E7E9F0"))
		sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		sub.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		sub.size = Vector2(s.x * 0.86, big * 3.0)
		sub.position = Vector2(s.x * 0.07, s.y * 0.34 + big * 1.6)
		talk_bg = ColorRect.new()
		talk_bg.color = Color(0.04, 0.04, 0.07, 0.78)
		talk_bg.size = Vector2(s.x * 0.6, big * 1.5)
		talk_bg.position = Vector2(s.x * 0.2, s.y * 0.06 + big * 0.6)
		talk_bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
		talk_bg.visible = false
		add_child(talk_bg)
		talk = _label(int(big * 0.4), Color.WHITE)
		talk.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		talk.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		talk.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		talk.size = talk_bg.size - Vector2(24, 8)
		talk.position = talk_bg.position + Vector2(12, 4)

	func _process(delta: float) -> void:
		if _say > 0.0:
			_say -= delta
			if _say <= 0.0:
				talk.text = ""
				talk_bg.visible = false

	func say(who: String, text: String, seconds: float = 3.5) -> void:
		# what a person says, shown near the top for a few seconds
		talk.text = (who + ": " + text) if who != "" else text
		talk_bg.visible = text != ""
		_say = seconds

	func set_score(text: String) -> void:
		if score != null:
			score.text = "Coins " + text

	func set_hp(n: int) -> void:
		if lives != null:
			lives.text = "Lives %d" % n

	func message(big_text: String, small_text: String = "") -> void:
		# a title / game over / win screen over the level; clear() hides it
		title.text = big_text
		sub.text = small_text
		shade.visible = true
		pad.visible = false

	func clear() -> void:
		title.text = ""
		sub.text = ""
		shade.visible = false
		pad.visible = true


class Figure extends Node3D:
	# a jointed character. set_motion() picks idle / walk / run / jump / fall; play() runs a one-off:
	# "attack", "hurt", "wave", "talk", and "die" (stays down).
	signal strike                    # the moment an attack lands
	signal finished(anim: String)    # a one-off ended
	const ONE := {"attack": 0.38, "hurt": 0.32, "wave": 1.3, "talk": 1.6, "die": 0.8}
	var kit: Node
	var height := 1.7
	var quad := false
	var j := {}
	var body: Node3D = null
	var hips_y := 0.0
	var state := "idle"
	var one := ""
	var one_t := 0.0
	var one_len := 0.0
	var struck := false
	var done_sent := false
	var dead := false
	var phase := 0.0
	var move := 0.0
	var grounded := true
	var vy := 0.0
	var ap: AnimationPlayer = null
	var clips := {}

	func play(anim: String) -> void:
		if dead or not ONE.has(anim):
			return
		if anim == "die":
			dead = true
		one = anim
		one_t = 0.0
		one_len = float(ONE[anim])
		struck = false
		done_sent = false

	func set_motion(amount: float, on_floor: bool = true, up_speed: float = 0.0) -> void:
		move = clamp(amount, 0.0, 1.0)
		grounded = on_floor
		vy = up_speed

	func busy() -> bool:
		return one != ""

	func _process(delta: float) -> void:
		if one != "":
			one_t += delta
			if one == "attack" and not struck and one_t >= one_len * 0.4:
				struck = true
				strike.emit()
			if one_t >= one_len:
				if one == "die":
					one_t = one_len
					if not done_sent:
						done_sent = true
						finished.emit("die")
				else:
					var was := one
					one = ""
					finished.emit(was)
		if one != "":
			state = one
		elif not grounded:
			state = "jump" if vy > 0.5 else "fall"
		elif move > 0.65:
			state = "run"
		elif move > 0.08:
			state = "walk"
		else:
			state = "idle"
		phase += delta * ((5.0 + 7.0 * move) if state in ["walk", "run"] else 1.7)
		var u: float = (one_t / one_len) if one != "" and one_len > 0.0 else 0.0
		var t := {}
		var bob := 0.0
		var tip := 0.0
		var roll := 0.0
		var lunge := 0.0
		var lift := 0.0
		if ap != null:
			_model_pose(u)
			if state == "attack":
				lunge = -0.16 * height * sin(u * PI)
			elif state == "die" and not clips.has("die"):
				tip = 1.5 * ease(u, 0.5)
				lift = 0.08 * height * u
		elif quad:
			var s := sin(phase)
			match state:
				"walk", "run":
					var a := 0.45 + 0.4 * move
					t["leg_fl"] = Vector3(s * a, 0, 0)
					t["leg_br"] = Vector3(s * a, 0, 0)
					t["leg_fr"] = Vector3(-s * a, 0, 0)
					t["leg_bl"] = Vector3(-s * a, 0, 0)
					t["tail"] = Vector3(0, sin(phase * 1.3) * 0.5, 0)
					t["head"] = Vector3(sin(phase * 2.0) * 0.06, 0, 0)
					bob = -absf(s) * 0.02 * height
				"jump", "fall":
					t["leg_fl"] = Vector3(0.8, 0, 0)
					t["leg_fr"] = Vector3(0.8, 0, 0)
					t["leg_bl"] = Vector3(-0.8, 0, 0)
					t["leg_br"] = Vector3(-0.8, 0, 0)
				"attack":
					t["head"] = Vector3(0.5 - 1.0 * u, 0, 0)
					lunge = -0.3 * height * sin(u * PI)
				"hurt":
					t["head"] = Vector3(0.5, 0, 0.3)
					t["torso"] = Vector3(0.15, 0, 0)
				"die":
					roll = 1.5 * ease(u, 0.5)
					lift = height * 0.2 * u
				_:
					t["tail"] = Vector3(0, s * 0.6, 0)
					t["head"] = Vector3(0, sin(phase * 0.4) * 0.3, 0)
					bob = s * 0.005 * height
		else:
			var s := sin(phase)
			var c := cos(phase)
			t["arm_l"] = Vector3(0, 0, -0.1)
			t["arm_r"] = Vector3(0, 0, 0.1)
			match state:
				"walk", "run":
					var a := 0.5 + 0.5 * move
					t["leg_l"] = Vector3(s * a, 0, 0)
					t["leg_r"] = Vector3(-s * a, 0, 0)
					t["knee_l"] = Vector3(-max(0.0, c) * a * 1.3, 0, 0)
					t["knee_r"] = Vector3(-max(0.0, -c) * a * 1.3, 0, 0)
					t["arm_l"] = Vector3(-s * a * 0.8, 0, -0.08)
					t["arm_r"] = Vector3(s * a * 0.8, 0, 0.08)
					t["elbow_l"] = Vector3(0.25 + 0.6 * move, 0, 0)
					t["elbow_r"] = Vector3(0.25 + 0.6 * move, 0, 0)
					t["torso"] = Vector3(-0.05 - 0.17 * move, s * 0.12, 0)
					t["head"] = Vector3(0.04 + 0.1 * move, -s * 0.08, 0)
					bob = -absf(s) * 0.022 * height * a
				"jump":
					t["leg_l"] = Vector3(0.95, 0, 0)
					t["knee_l"] = Vector3(-1.35, 0, 0)
					t["leg_r"] = Vector3(0.3, 0, 0)
					t["knee_r"] = Vector3(-0.7, 0, 0)
					t["arm_l"] = Vector3(2.5, 0, -0.3)
					t["arm_r"] = Vector3(2.5, 0, 0.3)
					t["torso"] = Vector3(-0.1, 0, 0)
				"fall":
					t["leg_l"] = Vector3(0.25, 0, 0)
					t["leg_r"] = Vector3(-0.15, 0, 0)
					t["knee_l"] = Vector3(-0.45, 0, 0)
					t["knee_r"] = Vector3(-0.3, 0, 0)
					t["arm_l"] = Vector3(0.3, 0, -1.35)
					t["arm_r"] = Vector3(0.3, 0, 1.35)
				"attack":
					var ax: float = lerp(0.3, 3.0, u / 0.3) if u < 0.3 else lerp(3.0, 0.45, ease((u - 0.3) / 0.7, 0.4))
					t["arm_r"] = Vector3(ax, 0, 0.1)
					t["elbow_r"] = Vector3(0.15, 0, 0)
					t["arm_l"] = Vector3(-0.45, 0, -0.25)
					t["torso"] = Vector3(-0.14, lerp(0.45, -0.5, u), 0)
					t["leg_l"] = Vector3(0.4, 0, 0)
					t["knee_l"] = Vector3(-0.3, 0, 0)
					t["leg_r"] = Vector3(-0.3, 0, 0)
				"hurt":
					t["torso"] = Vector3(0.35, 0, 0)
					t["head"] = Vector3(0.3, 0, 0)
					t["arm_l"] = Vector3(0.4, 0, -0.9)
					t["arm_r"] = Vector3(0.4, 0, 0.9)
					t["leg_l"] = Vector3(-0.2, 0, 0)
					t["leg_r"] = Vector3(0.2, 0, 0)
				"wave":
					t["arm_r"] = Vector3(0, 0, 2.55 + 0.35 * sin(one_t * 13.0))
					t["elbow_r"] = Vector3(0, 0, 0.35)
					t["head"] = Vector3(0, 0, 0.08)
				"talk":
					t["head"] = Vector3(0.08 * sin(one_t * 9.0), 0.15 * sin(one_t * 3.0), 0)
					t["arm_r"] = Vector3(0.9 + 0.2 * sin(one_t * 6.0), 0, 0.15)
					t["elbow_r"] = Vector3(1.0, 0, 0)
				"die":
					tip = 1.5 * ease(u, 0.5)
					lift = 0.07 * height * u
					t["arm_l"] = Vector3(0, 0, -1.2)
					t["arm_r"] = Vector3(0, 0, 1.2)
					t["leg_l"] = Vector3(0.1, 0, -0.12)
					t["leg_r"] = Vector3(-0.1, 0, 0.12)
				_:
					t["arm_l"] = Vector3(0, 0, -0.1 - 0.02 * s)
					t["arm_r"] = Vector3(0, 0, 0.1 + 0.02 * s)
					t["elbow_l"] = Vector3(0.12, 0, 0)
					t["elbow_r"] = Vector3(0.12, 0, 0)
					t["head"] = Vector3(0, sin(phase * 0.37) * 0.25, 0)
					bob = s * 0.006 * height
		var w: float = min(1.0, delta * (24.0 if state == "attack" else 13.0))
		for key in j:
			if key == "hips" or key == "hand_r":
				continue
			var n: Node3D = j[key]
			n.rotation = n.rotation.lerp(t.get(key, Vector3.ZERO), w)
		if j.has("hips"):
			var hp_n: Node3D = j["hips"]
			hp_n.position.y = lerp(hp_n.position.y, hips_y + bob, w)
		if body != null:
			body.rotation.x = lerp(body.rotation.x, tip, w)
			body.rotation.z = lerp(body.rotation.z, roll, w)
			body.position.z = lerp(body.position.z, lunge, w)
			body.position.y = lerp(body.position.y, lift, w)

	func _model_pose(_u: float) -> void:
		var want := ""
		for st in [state, {"run": "walk", "walk": "run", "fall": "jump", "jump": "fall"}.get(state, ""), "idle"]:
			if st != "" and clips.has(st):
				want = str(clips[st])
				break
		if want == "":
			return
		if ap.current_animation != want:
			ap.play(want, 0.15)
		ap.speed_scale = (0.6 + move) if state in ["walk", "run"] else 1.0


class Npc extends Node3D:
	var kit: Node
	var who := ""
	var lines: Array = []
	var talk_range := 2.6
	var figure: Node3D = null
	var hint: Label3D = null
	var said := 0
	var _near := false

	func _physics_process(delta: float) -> void:
		var p: Node3D = kit.player
		if p == null or not is_instance_valid(p):
			return
		var d := p.global_position - global_position
		d.y = 0.0
		var near := d.length() <= talk_range
		if d.length() <= talk_range * 1.8 and d.length() > 0.05 and figure != null:
			figure.rotation.y = lerp_angle(figure.rotation.y, atan2(-d.x, -d.z), min(1.0, delta * 6.0))
		if near and not _near and figure != null and not figure.busy():
			figure.play("wave")
		_near = near
		if hint != null:
			hint.visible = near and kit.playing

	func talk() -> void:
		var index: int = min(said, max(0, lines.size() - 1))
		var line := str(lines[index]) if lines.size() > 0 else ""
		said += 1
		if figure != null:
			figure.play("talk")
		kit._said(who, line, index)
