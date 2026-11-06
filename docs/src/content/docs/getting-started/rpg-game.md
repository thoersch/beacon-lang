---
title: The Ashen Crypt RPG
description: Play a native OpenGL dungeon crawler authored in Beacon.
---

# The Ashen Crypt

A turn-based dungeon crawler authored in Beacon using the game-local rules module and `std.graphics.gl` batched OpenGL drawing.

## Play (Windows)

From the repository root in PowerShell:

```powershell
./tools/run-rpg.ps1
```

Both the PowerShell and Bash Beacon launchers detect graphics programs and rebuild the independent OpenGL module from `native/opengl/Extension.cs` when the local source changes (requires .NET 8 SDK). You can therefore also run the game directly from Git Bash on Windows:

```bash
sh ./beacon.sh ./examples/rpg-ashen-crypt.beacon
```

The initial run recompiles the native extension to add the `batch` operation; subsequent runs reuse the built version until its source changes. The bundled DLL in this branch predates that operation.

## Controls and objective

- **WASD or arrow keys:** move one tile per turn. Move into a monster to attack.
- **H:** drink a potion (restores six health, consumes a turn).
- **R:** restart after a win or defeat.
- **Goal:** defeat all four enemies, then enter the gold gate at the southeast corner.
- Enemies pursue when nearby, fight in melee, and yield experience and gold when defeated. Three kills grant a level, increased power, and a full heal.

## Architecture

The portable rules live in `examples/rpg/rules.beacon` and reuse the typed hero, weapon and item vocabulary introduced by `examples/rpg-typed-inventory.beacon`. The renderer and keyboard input live in `examples/rpg-ashen-crypt.beacon`. A new OpenGL `batch` action draws rectangle sprites and a minimal embedded 5x7 bitmap font. One native call renders the entire frame.

Run the portable rules test with:

```bash
./beacon.sh examples/rpg-rules-smoke.beacon
```

The Windows framebuffer test, `examples/rpg-render-smoke.beacon`, checks that rectangles and font glyphs hit the correct pixels. Cross-platform CI also checks compiler self-hosting. The game deliberately uses no graphics packages or game engine.
