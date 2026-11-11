extends Node
# Hoola's test player for the 3D proof game (never shipped in a build): it plays with the SAME keys a person uses -
# start, walk a route, jump up the steps, step into the goal - and prints what really happened.

var route: Array[Vector2] = [Vector2(0, 8), Vector2(0, 5), Vector2(3, 2), Vector2(-3, 2), Vector2(0, -3),
	Vector2(0, -8), Vector2(0, -12.5)]
var at := 0
var t := 0.0
var started := false
var held := {}
var jump_wait := 0.0
var space_down := 0.0
var from := Vector3.ZERO
var top_y := 0.0
var done := false

func _key(code: int, down: bool) -> void:
	if bool(held.get(code, false)) == down:
		return
	held[code] = down
	var e := InputEventKey.new()
	e.keycode = code
	e.physical_keycode = code
	e.pressed = down
	Input.parse_input_event(e)

func _report(why: String) -> void:
	if done:
		return
	done = true
	var k := get_node("/root/Hoola3D")
	var main := get_node("/root/Main")
	var p: Node3D = k.player
	var moved := 0.0
	if p != null and is_instance_valid(p):
		moved = Vector2(p.global_position.x - from.x, p.global_position.z - from.z).length()
	print("PROOFBOT " + JSON.stringify({"why": why, "state": int(main.state), "coins": int(k.coins), "coins_total": int(k.coins_total),
		"hp": int(p.hp) if p != null and is_instance_valid(p) else -1, "seconds": snappedf(t, 0.1), "moved_m": snappedf(moved, 0.1),
		"top_y": snappedf(top_y, 0.01), "enemies_left": int(k.enemies_left)}))
	get_tree().quit()

func _physics_process(delta: float) -> void:
	t += delta
	var k := get_node_or_null("/root/Hoola3D")
	var main := get_node_or_null("/root/Main")
	if k == null or main == null:
		return
	if space_down > 0.0:
		space_down -= delta
		if space_down <= 0.0:
			_key(KEY_SPACE, false)
	if not started:
		if t > 0.6:
			started = true
			_key(KEY_SPACE, true)
			space_down = 0.12
			if k.player != null:
				from = k.player.global_position
		return
	var st := int(main.state)
	if st == 3:
		_report("win")
		return
	if st == 2:
		_report("game over")
		return
	if t > 90.0:
		_report("time ran out")
		return
	var p: CharacterBody3D = k.player
	if p == null or not is_instance_valid(p) or st != 1:
		return
	var pos := p.global_position
	top_y = max(top_y, pos.y)
	var d := Vector2(route[at].x - pos.x, route[at].y - pos.z)
	if d.length() < 0.7 and at < route.size() - 1:
		at += 1
	_key(KEY_A, d.x < -0.3)
	_key(KEY_D, d.x > 0.3)
	_key(KEY_W, d.y < -0.3)
	_key(KEY_S, d.y > 0.3)
	jump_wait -= delta
	if pos.z < -5.6 and p.is_on_floor() and jump_wait <= 0.0 and space_down <= 0.0:
		jump_wait = 0.45
		_key(KEY_SPACE, true)
		space_down = 0.1
