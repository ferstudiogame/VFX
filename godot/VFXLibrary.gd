extends Node3D
## Reproduce un efecto GLB exportado desde Blender. No genera VFX en Godot.
## Ejemplo:
## $VFXLibrary.spawn_effect("res://vfx/electric_arc/electric_arc.glb", self, Transform3D.IDENTITY)

func spawn_effect(glb_path: String, target: Node3D, local_transform: Transform3D = Transform3D.IDENTITY) -> Node3D:
    if target == null:
        push_error("VFXLibrary: target es null")
        return null
    var packed := load(glb_path) as PackedScene
    if packed == null:
        push_error("VFXLibrary: no se pudo cargar " + glb_path)
        return null
    var instance := packed.instantiate() as Node3D
    if instance == null:
        push_error("VFXLibrary: el GLB no tiene una raíz Node3D")
        return null
    target.add_child(instance)
    instance.transform = local_transform
    var player := _find_animation_player(instance)
    if player == null:
        push_warning("VFXLibrary: el GLB no contiene AnimationPlayer: " + glb_path)
        return instance
    var clips := player.get_animation_list()
    if clips.is_empty():
        push_warning("VFXLibrary: no hay clips de animación: " + glb_path)
        return instance
    player.animation_finished.connect(func(_clip): instance.queue_free(), CONNECT_ONE_SHOT)
    player.play(clips[0])
    return instance

func _find_animation_player(node: Node) -> AnimationPlayer:
    if node is AnimationPlayer:
        return node as AnimationPlayer
    for child in node.get_children():
        var found := _find_animation_player(child)
        if found != null:
            return found
    return null
