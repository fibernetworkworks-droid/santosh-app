extends Node
# Hoola3D self-test (never shipped): four small scenes, each proving one rule of the kit in the real engine.
# Prints one line: KITTEST {"hit": .., "stomp": .., "fall": .., "touch": .., "coin": .., "lift": .., "figures": ..,
# "attack": .., "npc": .., "model": ..}

var out := {}
var level: Node3D = null
var fell := 0

func _ready() -> void:
	Hoola3D.player_fell.connect(func() -> void: fell += 1)
	await _hit()
	await _stomp()
	await _fall()
	await _touch()
	await _coin_and_lift()
	await _figures()
	await _attack()
	await _npc()
	await _model()
	print("KITTEST " + JSON.stringify(out))
	get_tree().quit()

func _fresh(with_ground: bool = true) -> void:
	if level != null:
		remove_child(level)
		level.queue_free()
	Hoola3D.reset()
	level = Hoola3D.world(self)
	if with_ground:
		Hoola3D.ground(level, Vector2(30.0, 30.0))

func _wait(seconds: float) -> void:
	var frames := int(seconds * 60.0)
	for i in frames:
		await get_tree().physics_frame

func _key(code: int, down: bool) -> void:
	var e := InputEventKey.new()
	e.keycode = code
	e.physical_keycode = code
	e.pressed = down
	Input.parse_input_event(e)

func _hit() -> void:
	# walking into a guard costs exactly one life, and the second touch inside the safe time costs nothing
	_fresh()
	var p := Hoola3D.spawn_player(level, Vector3(0.0, 0.1, 4.0))
	Hoola3D.follow_camera(p, 7.0)
	Hoola3D.enemy(level, Vector3(0.0, 0.0, 0.0))
	await _wait(0.3)
	_key(KEY_W, true)
	await _wait(1.6)
	_key(KEY_W, false)
	out["hit"] = {"hp": int(p.hp), "ok": int(p.hp) == 2}

func _stomp() -> void:
	# landing on a guard from above removes it and costs no life
	_fresh()
	var p := Hoola3D.spawn_player(level, Vector3(0.0, 4.0, 0.0))
	Hoola3D.follow_camera(p, 7.0)
	Hoola3D.enemy(level, Vector3(0.0, 0.0, 0.0))
	await _wait(1.5)
	out["stomp"] = {"hp": int(p.hp), "left": int(Hoola3D.enemies_left), "ok": int(p.hp) == 3 and int(Hoola3D.enemies_left) == 0}

func _fall() -> void:
	# no ground: the player falls, comes back to the start and loses one life
	_fresh(false)
	fell = 0
	var p := Hoola3D.spawn_player(level, Vector3(0.0, 0.0, 0.0))
	Hoola3D.follow_camera(p, 7.0)
	Hoola3D.block(level, Vector3(0.0, 40.0, 0.0), Vector3(1.0, 1.0, 1.0))
	await _wait(2.6)
	out["fall"] = {"hp": int(p.hp), "fell": fell, "y": snappedf(p.global_position.y, 0.1), "ok": fell >= 1 and int(p.hp) <= 2 and p.global_position.y > -14.0}

func _touch() -> void:
	# the left stick walks the player forward, the jump button jumps. A headless engine has no window, so the touch
	# events are handed to the kit directly here; kit3d.browser_touch() proves the same thing in a real browser.
	_fresh()
	var p := Hoola3D.spawn_player(level, Vector3(0.0, 0.1, 6.0))
	Hoola3D.follow_camera(p, 7.0)
	await _wait(0.3)
	var s := get_viewport().get_visible_rect().size
	var down := InputEventScreenTouch.new()
	down.index = 0
	down.pressed = true
	down.position = Vector2(s.x * 0.2, s.y * 0.8)
	Hoola3D._input(down)
	var drag := InputEventScreenDrag.new()
	drag.index = 0
	drag.position = Vector2(s.x * 0.2, s.y * 0.8 - 200.0)
	drag.relative = Vector2(0.0, -200.0)
	Hoola3D._input(drag)
	await _wait(1.0)
	var walked := 6.0 - p.global_position.z
	var jb := Hoola3D.jump_button().get_center()
	var tap := InputEventScreenTouch.new()
	tap.index = 1
	tap.pressed = true
	tap.position = jb
	Hoola3D._input(tap)
	var top := 0.0
	for i in 40:
		await get_tree().physics_frame
		top = max(top, p.global_position.y)
	var up := InputEventScreenTouch.new()
	up.index = 0
	up.pressed = false
	up.position = drag.position
	Hoola3D._input(up)
	var up1 := InputEventScreenTouch.new()
	up1.index = 1
	up1.pressed = false
	up1.position = jb
	Hoola3D._input(up1)
	out["touch"] = {"walked_m": snappedf(walked, 0.1), "jump_m": snappedf(top, 0.01), "ok": walked > 3.0 and top > 1.2}

func _coin_and_lift() -> void:
	# a coin under the player is taken at once; a lift carries the player up
	_fresh()
	var p := Hoola3D.spawn_player(level, Vector3(5.0, 0.6, 5.0))
	Hoola3D.follow_camera(p, 7.0)
	Hoola3D.coin(level, Vector3(5.0, 1.0, 5.0))
	Hoola3D.moving_block(level, Vector3(5.0, 0.25, 5.0), Vector3(5.0, 3.25, 5.0), Vector3(3.0, 0.5, 3.0), Color("#8B7BFF"), 1.0)
	var top := 0.0
	for i in 90:
		await get_tree().physics_frame
		top = max(top, p.global_position.y)
	out["coin"] = {"coins": int(Hoola3D.coins), "of": int(Hoola3D.coins_total), "ok": int(Hoola3D.coins) == 1}
	out["lift"] = {"top_y": snappedf(top, 0.01), "ok": top > 2.5}

func _press(code: int) -> void:
	_key(code, true)
	await _wait(0.08)
	_key(code, false)

func _figures() -> void:
	# every ready-made look is built; a walking figure swings its legs opposite ways, a standing one stops,
	# an attack lands once and ends, and "die" leaves the figure lying down
	_fresh()
	var made := 0
	var joints_min := 99
	var x := -10.0
	for name in Hoola3D.LOOKS:
		var g: Node3D = Hoola3D.figure(level, Vector3(x, 0.0, -6.0), Hoola3D.look(name))
		x += 2.0
		made += 1
		joints_min = min(joints_min, g.j.size())
	var f: Node3D = Hoola3D.figure(level, Vector3(0.0, 0.0, 0.0), Hoola3D.look("guard"))
	f.set_motion(1.0)
	var swing := 0.0
	var opposite := true
	for i in 50:
		await get_tree().process_frame
		var l: float = f.j["leg_l"].rotation.x
		var r: float = f.j["leg_r"].rotation.x
		swing = max(swing, absf(l))
		if absf(l) > 0.25 and l * r > 0.0:
			opposite = false
	f.set_motion(0.0)
	await _wait(0.7)
	var rest: float = absf(f.j["leg_l"].rotation.x)
	var hits := [0]
	var ended := [""]
	f.strike.connect(func() -> void: hits[0] += 1)
	f.finished.connect(func(a: String) -> void: ended[0] = a)
	f.play("attack")
	await _wait(0.7)
	var back := str(f.state)
	var ended_attack := str(ended[0])
	f.play("die")
	await _wait(1.3)
	var tipped: float = f.body.rotation.x
	f.play("wave")                       # a fallen figure does not get up
	await _wait(0.2)
	var q: Node3D = Hoola3D.figure(level, Vector3(4.0, 0.0, 0.0), Hoola3D.look("dog"))
	q.set_motion(0.6)
	var qswing := 0.0
	for i in 40:
		await get_tree().process_frame
		qswing = max(qswing, absf(q.j["leg_fl"].rotation.x))
	out["figures"] = {"made": made, "joints_min": joints_min, "swing": snappedf(swing, 0.01), "opposite": opposite,
		"rest": snappedf(rest, 0.01), "strikes": hits[0], "ended": ended_attack, "ended_last": ended[0], "back": back, "tipped": snappedf(tipped, 0.01),
		"still_down": str(f.state) == "die", "quad_swing": snappedf(qswing, 0.01),
		"ok": made == Hoola3D.LOOKS.size() and joints_min >= 7 and swing > 0.5 and opposite and rest < 0.1 and hits[0] == 1
			and ended_attack == "attack" and ended[0] == "die" and back == "idle" and tipped > 1.2 and str(f.state) == "die" and qswing > 0.25}

func _attack() -> void:
	# a hero with a sword: two strikes fell a foe with 2 health in front; the foe behind is untouched; no life is lost
	_fresh()
	var p := Hoola3D.spawn_hero(level, Vector3(0.0, 0.1, 3.0), Hoola3D.look("hero", {"item": "sword"}))
	Hoola3D.follow_camera(p, 7.0)
	var front: Area3D = Hoola3D.foe(level, Vector3(0.0, 0.0, 1.8), {}, Vector3.ZERO, 0.0, 0.0, 2)
	var behind: Area3D = Hoola3D.foe(level, Vector3(0.0, 0.0, 4.6), {}, Vector3.ZERO, 0.0, 0.0, 2)
	var gone := [0]
	Hoola3D.enemy_defeated.connect(func(_left: int) -> void: gone[0] += 1)
	await _wait(0.4)
	await _press(KEY_F)
	await _wait(0.6)
	var after_one := int(front.hp)
	var staggered := str(front.figure.state)
	await _wait(0.3)
	await _press(KEY_F)
	await _wait(0.6)
	var left := int(Hoola3D.enemies_left)
	var fell := is_instance_valid(front) and bool(front.dead)
	await _wait(1.6)
	out["attack"] = {"can": bool(p.can_attack), "after_one": after_one, "left": left, "defeated": gone[0], "fell": fell,
		"freed": not is_instance_valid(front), "behind_hp": int(behind.hp), "hp": int(p.hp), "button": bool(Hoola3D.act_on),
		"ok": bool(p.can_attack) and after_one == 1 and left == 1 and gone[0] == 1 and fell and not is_instance_valid(front)
			and int(behind.hp) == 2 and int(p.hp) == 3 and bool(Hoola3D.act_on)}

func _npc() -> void:
	# a person beside the player says her lines in order, the last one repeats, and the HUD shows what was said;
	# the same key far from anyone says nothing
	_fresh()
	var p := Hoola3D.spawn_hero(level, Vector3(0.0, 0.1, 3.0))
	Hoola3D.follow_camera(p, 7.0)
	var hud: CanvasLayer = Hoola3D.make_hud(self)
	var n: Node3D = Hoola3D.npc(level, Vector3(1.5, 0.0, 2.0), "Dadi", ["Namaste beta", "Collect five diyas", "Then come to the temple"])
	var far: Node3D = Hoola3D.npc(level, Vector3(12.0, 0.0, -12.0), "Raju", ["Hello"])
	var heard: Array = []
	Hoola3D.npc_talked.connect(func(who: String, line: int) -> void: heard.append("%s%d" % [who, line]))
	await _wait(0.5)
	var waved := str(n.figure.state)
	for i in 4:
		await _press(KEY_F)
		await _wait(0.25)
	var shown := str(hud.talk.text)
	var turned: float = absf(n.figure.rotation.y)
	remove_child(hud)
	hud.queue_free()
	out["npc"] = {"heard": heard, "shown": shown, "waved": waved, "far_said": int(far.said), "turned": snappedf(turned, 0.01),
		"ok": heard == ["Dadi0", "Dadi1", "Dadi2", "Dadi2"] and shown == "Dadi: Then come to the temple" and int(far.said) == 0
			and turned > 0.3}

func _model() -> void:
	# a real animated 3D model (Kenney's CC0 character) as a figure: sized to the height asked for, and its own clips
	# are found and played - walk while moving, jump in the air, idle when standing
	_fresh()
	var ps: Variant = load("res://char.glb")
	if ps == null or not (ps is PackedScene):
		out["model"] = {"ok": false, "why": "the model did not import"}
		return
	var f: Node3D = Hoola3D.figure_from(level, Vector3(0.0, 0.0, 0.0), (ps as PackedScene).instantiate() as Node3D, {"height": 1.6})
	var acc: Array = []
	Hoola3D._bounds(f, Transform3D.IDENTITY, acc)
	var box: AABB = acc[0]
	for b in acc:
		box = box.merge(b)
	f.set_motion(1.0)
	await _wait(0.4)
	var walking := str(f.ap.current_animation)
	f.set_motion(0.0, false, 3.0)
	await _wait(0.3)
	var jumping := str(f.ap.current_animation)
	f.set_motion(0.0)
	await _wait(0.3)
	var idle := str(f.ap.current_animation)
	out["model"] = {"clips": f.clips, "tall": snappedf(box.size.y, 0.01), "walking": walking, "jumping": jumping, "idle": idle,
		"ok": f.clips.has("idle") and f.clips.has("walk") and f.clips.has("jump") and absf(box.size.y - 1.6) < 0.1
			and walking == str(f.clips["walk"]) and jumping == str(f.clips["jump"]) and idle == str(f.clips["idle"])}
