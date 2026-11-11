extends Node
# Hoola3D - Hoola's own 3D gameplay kit (written by Hoola, never by the model; v1).
# One level of a small 3D game from proved pieces: a world with sky and sun, ground and blocks, a player who walks
# and jumps (keyboard AND touch), a follow / first-person camera, things to collect, enemies that patrol or chase,
# a goal, and a HUD with on-screen controls. Every piece is built in code, so it exports to the web as it is.

const VERSION := 1

signal coin_taken(total: int)
signal player_hit(hp: int)
signal player_fell
signal goal_reached
signal enemy_stomped(left: int)

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

func _input(event: InputEvent) -> void:
	if event is InputEventKey:
		var k := event as InputEventKey
		if k.pressed and not k.echo and (k.physical_keycode == KEY_SPACE or k.keycode == KEY_SPACE):
			_jump = true
		return
	if event is InputEventScreenTouch:
		var t := event as InputEventScreenTouch
		if t.pressed:
			if jump_button().grow(12.0).has_point(t.position):
				_jump = true
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
	enemies_left = max(0, enemies_left - 1)
	e.queue_free()
	if player != null and is_instance_valid(player):
		player.velocity.y = 7.0
	enemy_stomped.emit(enemies_left)

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

	func _ready() -> void:
		body_entered.connect(_on_body)

	func _physics_process(delta: float) -> void:
		if not kit.playing:
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
			return
		var move := step.normalized() * speed * delta
		global_position += move
		rotation.y = lerp_angle(rotation.y, atan2(-move.x, -move.z), min(1.0, delta * 8.0))

	func _on_body(body: Node) -> void:
		if body != kit.player or not kit.playing:
			return
		var p := body as CharacterBody3D
		if p.velocity.y < -1.0 and p.global_position.y > global_position.y + 0.35:
			kit._stomped(self)
		else:
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


class Hud extends CanvasLayer:
	var kit: Node
	var score: Label
	var lives: Label
	var title: Label
	var sub: Label
	var shade: ColorRect
	var pad: Control

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
