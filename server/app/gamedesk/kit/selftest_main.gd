extends Node
# Hoola3D self-test (never shipped): four small scenes, each proving one rule of the kit in the real engine.
# Prints one line: KITTEST {"hit": .., "stomp": .., "fall": .., "touch": .., "coin": .., "lift": ..}

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
