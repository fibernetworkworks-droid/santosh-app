extends Node
# Diya Run 3D - Hoola's 3D proof game. Every piece comes from the Hoola3D kit: this file only lays out one level
# and runs the screens (title -> playing -> win / game over).

enum S { TITLE, PLAYING, OVER, WIN }

const NEED := 5                      # coins needed before the goal counts

var state: int = S.TITLE
var level: Node3D = null
var hud: CanvasLayer = null

func _ready() -> void:
	Hoola3D.coin_taken.connect(_on_coin)
	Hoola3D.player_hit.connect(_on_hit)
	Hoola3D.goal_reached.connect(_on_goal)
	_build()
	_title()

func _build() -> void:
	if level != null:
		remove_child(level)
		level.queue_free()
	if hud != null:
		remove_child(hud)
		hud.queue_free()
	Hoola3D.reset()
	level = Hoola3D.world(self, Color("#1B2A6B"), Color("#F2A65A"))
	Hoola3D.ground(level, Vector2(36.0, 36.0), Color("#3F7A4A"))
	# walls round the courtyard
	Hoola3D.block(level, Vector3(0.0, 1.0, -18.5), Vector3(38.0, 2.0, 1.0), Color("#7A5A3C"))
	Hoola3D.block(level, Vector3(0.0, 1.0, 18.5), Vector3(38.0, 2.0, 1.0), Color("#7A5A3C"))
	Hoola3D.block(level, Vector3(-18.5, 1.0, 0.0), Vector3(1.0, 2.0, 36.0), Color("#7A5A3C"))
	Hoola3D.block(level, Vector3(18.5, 1.0, 0.0), Vector3(1.0, 2.0, 36.0), Color("#7A5A3C"))
	# two steps up to the goal
	Hoola3D.block(level, Vector3(0.0, 0.5, -8.0), Vector3(5.0, 1.0, 3.0), Color("#C98A4B"))
	Hoola3D.block(level, Vector3(0.0, 1.0, -12.0), Vector3(6.0, 2.0, 5.0), Color("#B5763A"))
	Hoola3D.goal(level, Vector3(0.0, 2.0, -12.5))
	# a lift to a high coin
	Hoola3D.moving_block(level, Vector3(9.0, 0.25, 3.0), Vector3(9.0, 2.75, 3.0), Vector3(3.0, 0.5, 3.0), Color("#8B7BFF"), 2.5)
	for p in [Vector3(0, 1, 8), Vector3(0, 1, 5), Vector3(3, 1, 2), Vector3(-3, 1, 2), Vector3(0, 1, -3),
			Vector3(0, 2, -8), Vector3(9, 4, 3), Vector3(-9, 1, -4)]:
		Hoola3D.coin(level, p)
	Hoola3D.enemy(level, Vector3(-6.0, 0.0, 0.0), Vector3(6.0, 0.0, 0.0), 2.6)
	Hoola3D.enemy(level, Vector3(5.0, 0.0, -6.0), Vector3.ZERO, 3.2, 5.0, Color("#E255A8"))
	for t in [Vector3(-13, 0, -13), Vector3(13, 0, -13), Vector3(-14, 0, 6), Vector3(14, 0, 10), Vector3(-10, 0, 13), Vector3(11, 0, -3)]:
		Hoola3D.tree(level, t, 3.2)
	var p3 := Hoola3D.spawn_player(level, Vector3(0.0, 0.2, 13.0))
	Hoola3D.follow_camera(p3, 7.5)
	hud = Hoola3D.make_hud(self)

func _title() -> void:
	state = S.TITLE
	Hoola3D.playing = false
	hud.message("Diya Run 3D", "Tap or press Space to start\nCollect %d coins, then reach the green light\nMove: arrows or the left stick · Jump: Space or the button · Look: drag" % NEED)
	HoolaProbe.state("state", "title")

func _start() -> void:
	state = S.PLAYING
	Hoola3D.playing = true
	Hoola3D.take_jump()
	hud.clear()
	HoolaProbe.state("state", "playing")
	HoolaProbe.state("score", 0)

func _input(event: InputEvent) -> void:
	if state == S.PLAYING:
		return
	var go := false
	if event is InputEventScreenTouch and (event as InputEventScreenTouch).pressed:
		go = true
	if event is InputEventKey and (event as InputEventKey).pressed and not (event as InputEventKey).echo:
		var k := (event as InputEventKey).keycode
		go = k == KEY_SPACE or k == KEY_ENTER
	if not go:
		return
	if state != S.TITLE:
		_build()
	_start()

func _on_coin(total: int) -> void:
	if total == NEED:
		HoolaProbe.event("level_up")

func _on_hit(hp: int) -> void:
	if hp <= 0 and state == S.PLAYING:
		state = S.OVER
		Hoola3D.playing = false
		hud.message("Game over", "Coins %d of %d\nTap to try again" % [Hoola3D.coins, Hoola3D.coins_total])
		HoolaProbe.state("state", "game_over")
		HoolaProbe.event("game_over")

func _on_goal() -> void:
	if state != S.PLAYING:
		return
	if Hoola3D.coins < NEED:
		return
	state = S.WIN
	Hoola3D.playing = false
	hud.message("You made it!", "Coins %d of %d\nTap to play again" % [Hoola3D.coins, Hoola3D.coins_total])
	HoolaProbe.state("state", "win")
	HoolaProbe.event("win")
