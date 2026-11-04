# Port spec: `P_GiveArtifact` (Heretic)

Source: `src/heretic/p_inter.c`

- `P_GiveArtifact`: lines 417–458 (header comment at 417–423, body at 425–458)

The function is short and has no side effects beyond the `player_t` fields
listed below. It makes no calls, uses no randomness, plays no sounds and
prints no messages. It reads one `mobj_t` field (`flags`) and writes none.
The callers handle messages, the dormant-artifact state change and sound.

Stay-C fence: "Rust writes only through pointers it's handed; globals, RNG and thinker list stay in C."

---

## Shared types

| Type | Definition | Notes |
|---|---|---|
| `boolean` | `src/doomtype.h` (per `docs/port-specs/p_inter-givebody-givearmor.md`: `typedef int boolean;` at line 110 via `<stdbool.h>`, enum fallback at 114–118) | Return values are always exactly `false` (0) or `true` (1). |
| `player_t` | `src/heretic/doomdef.h:422` (`struct player_s`) | Passed by pointer and dereferenced with no NULL check. |
| `mobj_t` | `src/heretic/doomdef.h:150–193` (`struct mobj_s`); `int flags;` at line 175 | Optional. May be `NULL` (cheat callers). Only `flags` is read. |
| `artitype_t` | `src/heretic/doomdef.h:365–379` | `arti_none` = 0 … `arti_teleport` = 10, `NUMARTIFACTS` = 11. |
| `inventory_t` | `src/heretic/doomdef.h:408–412` | `int type;` (410), `int count;` (411). |

Relevant `player_t` fields (`src/heretic/doomdef.h`):

| Field | Line | Type | Comment in source |
|---|---|---|---|
| `inventory` | 440 | `inventory_t[NUMINVENTORYSLOTS]` (14, line 407) | |
| `readyArtifact` | 441 | `artitype_t` | |
| `artifactCount` | 442 | `int` | |
| `inventorySlotNum` | 443 | `int` | |
| `itemcount` | 458 | `int` | "for intermission" (shared with `killcount`, `secretcount`) |

---

## 1. `P_GiveArtifact`

### Signature

```c
boolean P_GiveArtifact(player_t * player, artitype_t arti, mobj_t * mo);
```

- Defined at `src/heretic/p_inter.c:425`.
- Prototype at `src/heretic/p_local.h:273`, so it is visible to other modules
  (`sb_bar.c` calls it).
- Header comment: "Returns true if artifact accepted."
- `src/hexen/p_inter.c:789` defines a separate Hexen `P_GiveArtifact`. It is
  out of scope.

Proposed Rust signature. There is no Rust code in the repo yet (no
`Cargo.toml` or `*.rs` found), so the FFI conventions are not confirmed:

```rust
#[no_mangle]
pub unsafe extern "C" fn P_GiveArtifact(
    player: *mut player_t,   // non-NULL, written through
    arti: artitype_t,        // C enum, ABI = int
    mo: *const mobj_t,       // may be NULL; only `flags` read
) -> boolean                 // C int, 0 or 1
```

### Reference implementation (verbatim, p_inter.c:425-458)

```c
boolean P_GiveArtifact(player_t * player, artitype_t arti, mobj_t * mo)
{
    int i;

    i = 0;
    while (player->inventory[i].type != arti && i < player->inventorySlotNum)
    {
        i++;
    }
    if (i == player->inventorySlotNum)
    {
        player->inventory[i].count = 1;
        player->inventory[i].type = arti;
        player->inventorySlotNum++;
    }
    else
    {
        if (player->inventory[i].count >= 16)
        {                       // Player already has 16 of this item
            return (false);
        }
        player->inventory[i].count++;
    }
    if (player->artifactCount == 0)
    {
        player->readyArtifact = arti;
    }
    player->artifactCount++;
    if (mo && (mo->flags & MF_COUNTITEM))
    {
        player->itemcount++;
    }
    return (true);
}
```

### Algorithm / return-value rules

1. Linear search: starting at `i = 0`, advance while
   `inventory[i].type != arti && i < inventorySlotNum` (line 430). **Order
   matters:** `inventory[i].type` is read *before* the bound test, so when
   `i == inventorySlotNum` the slot one past the live list is read.
2. **New slot** (`i == inventorySlotNum`, line 434): set
   `inventory[i].count = 1`, `inventory[i].type = arti`, then
   `inventorySlotNum++` (lines 436–438).
3. **Existing slot**: if `inventory[i].count >= 16`, **return `false`**
   (lines 442–445). Nothing at all is written on this path. Otherwise
   `inventory[i].count++` (line 446).
4. If `artifactCount == 0` *before* the increment, set
   `readyArtifact = arti` (lines 448–451).
5. `artifactCount++` (line 452).
6. If `mo != NULL` and `mo->flags & MF_COUNTITEM`, `itemcount++`
   (lines 453–456).
7. **Return `true`** (line 457).

Porting notes:

- **Stale slot past the end.** `P_PlayerRemoveArtifact`
  (`src/heretic/p_user.c:836`) compacts the list by shifting entries down
  (p_user.c:844–847) and decrementing `inventorySlotNum` (p_user.c:848). It
  does not clear the old last entry, so `inventory[inventorySlotNum]` can hold
  a stale `type`/`count`. The search may match that stale type, but it then
  stops at `i == inventorySlotNum` anyway, and step 2 overwrites both fields.
  So the result is the same either way. A Rust port must still read the slot
  the same way, or deliberately bound-check first. Either gives identical
  results, but reading index 14 would be out of bounds (see the next note).
- **No bound against `NUMINVENTORYSLOTS` (14, doomdef.h:407).** If
  `inventorySlotNum` were 14, line 430 would read and lines 436–437 would
  write `inventory[14]`, out of bounds. This can't happen in-tree, because
  there are only 10 artifact types (doomdef.h:367–377) and each takes one
  slot. A Rust port should index through the raw pointer the same way, or add
  a `debug_assert!(inventorySlotNum < 14)` that does not change release
  behavior. It must not silently clamp.
- The cap `16` is an inline literal (line 442). The test is `>=`, so the
  17th pickup is refused.
- `arti` is not validated. In-tree callers only pass 1–10 (see call sites).
- `readyArtifact` is set from `arti` only when the player had *zero*
  artifacts in total (`artifactCount == 0`), not when a new slot is created.
- `mo` is only used for the `MF_COUNTITEM` test. Its `flags` value is read
  as `int` (doomdef.h:175), and `MF_COUNTITEM` is `0x800000`
  (doomdef.h:240).
- `player` is dereferenced with no NULL check. Keep the precondition that it
  is non-NULL.

### Fields and globals read / written

| Item | Kind | Read | Written | Where (p_inter.c line) |
|---|---|---|---|---|
| `player->inventory[i].type` | `player_t` field (`inventory_t.type`) | ✔ | ✔ (new-slot path only) | read 430; written 437 |
| `player->inventory[i].count` | `player_t` field (`inventory_t.count`) | ✔ (existing-slot path) | ✔ (only on the `true` path) | read 442; written 436 (`= 1`), 446 (`++`) |
| `player->inventorySlotNum` | `player_t` field | ✔ | ✔ (new-slot path only) | read 430, 434; written 438 |
| `player->artifactCount` | `player_t` field | ✔ (only on the `true` path) | ✔ (only on the `true` path) | read 448; written 452 |
| `player->readyArtifact` | `player_t` field | | ✔ (only if `artifactCount == 0`) | 450 |
| `player->itemcount` | `player_t` field | | ✔ (only if `mo` has `MF_COUNTITEM`) | 455 |
| `mo->flags` | `mobj_t` field (`doomdef.h:175`) | ✔ (only if `mo != NULL`) | | 453 |
| `arti` | parameter | ✔ | | 430, 437, 450 |
| Globals | none | – | – | It touches no global variables, no RNG, no thinker list. |

### What stays in C (stay-C fence)

"Rust writes only through pointers it's handed; globals, RNG and thinker list stay in C."

The ported function writes only through `player` and reads only through
`mo`. Everything below stays in C and is out of scope for this port:

| Stays in C | Where | Why |
|---|---|---|
| `P_TouchSpecialThing` (all 10 artifact cases) | `src/heretic/p_inter.c:546`, cases 653–722 | Caller. It reads `special->sprite`, and its other paths touch globals (`netgame`, line 622). |
| `PIT_CheckThing` → `P_TouchSpecialThing` | `src/heretic/p_map.c:434` | Movement and collision code. |
| `P_SetDormantArtifact` | `src/heretic/p_inter.c:469–482` | Reads global `deathmatch` (472). `P_SetMobjState` goes through the state machine and thinker list (475, 479). `S_StartSound` (481). |
| `P_SetMessage` | called at p_inter.c:656, 663, … 719 | Player message and HUD. |
| `CheatArtifact3Func` | `src/heretic/sb_bar.c:1178–1224` | Reads global `gamemode` (1193, 1208). Reached through `HandleCheats` (sb_bar.c:1015), which reads `netgame`, `gameskill`, `players[consoleplayer]` (1020–1033). |
| Inventory consumers | `P_PlayerRemoveArtifact` (`p_user.c:836`), `G_PlayerFinishLevel` (`g_game.c:1312–1327`), save/load (`p_saveg.c:413–417`, `582–586`), status bar (`sb_bar.c:898–981`) | They share the same fields, so the layout of `player_t` must not change. |

### Constants

| Name | Value | Defined at |
|---|---|---|
| (literal) max count per artifact | `16` | Inline literal at `src/heretic/p_inter.c:442` (no `#define`) |
| `MF_COUNTITEM` | `0x800000` | `src/heretic/doomdef.h:240` |
| `NUMINVENTORYSLOTS` | `14` | `src/heretic/doomdef.h:407` (not checked by this function) |
| `arti_none` … `arti_teleport`, `NUMARTIFACTS` | `0` … `10`, `11` | `src/heretic/doomdef.h:367–378` |
| `false` / `true` | `0` / `1` | `src/doomtype.h` (see Shared types) |

### Call sites under `src/heretic`

| # | File:line | Enclosing function | `arti` | `mo` | Trigger | Use of return value |
|---|---|---|---|---|---|---|
| 1 | `src/heretic/p_inter.c:654` | `P_TouchSpecialThing` (p_inter.c:546), `case SPR_PTN2` | `arti_health` | `special` | Walking over a **Quartz Flask** (`TXT_ARTIHEALTH`, `src/heretic/dstrings.h:33`). Reached from `src/heretic/p_map.c:434` (`PIT_CheckThing`). | On `true`, message and `P_SetDormantArtifact`. Always `return` (no common pickup tail). |
| 2 | `src/heretic/p_inter.c:661` | same, `case SPR_SOAR` | `arti_fly` | `special` | **Wings of Wrath** (`TXT_ARTIFLY`, dstrings.h:34) | Same as #1. |
| 3 | `src/heretic/p_inter.c:668` | same, `case SPR_INVU` | `arti_invulnerability` | `special` | **Ring of Invincibility** (`TXT_ARTIINVULNERABILITY`, dstrings.h:35) | Same as #1. |
| 4 | `src/heretic/p_inter.c:675` | same, `case SPR_PWBK` | `arti_tomeofpower` | `special` | **Tome of Power** (`TXT_ARTITOMEOFPOWER`, dstrings.h:36) | Same as #1. |
| 5 | `src/heretic/p_inter.c:682` | same, `case SPR_INVS` | `arti_invisibility` | `special` | **Shadowsphere** (`TXT_ARTIINVISIBILITY`, dstrings.h:37) | Same as #1. |
| 6 | `src/heretic/p_inter.c:689` | same, `case SPR_EGGC` | `arti_egg` | `special` | **Morph Ovum** (`TXT_ARTIEGG`, dstrings.h:38) | Same as #1. |
| 7 | `src/heretic/p_inter.c:696` | same, `case SPR_SPHL` | `arti_superhealth` | `special` | **Mystic Urn** (`TXT_ARTISUPERHEALTH`, dstrings.h:39) | Same as #1. |
| 8 | `src/heretic/p_inter.c:703` | same, `case SPR_TRCH` | `arti_torch` | `special` | **Torch** (`TXT_ARTITORCH`, dstrings.h:40) | Same as #1. |
| 9 | `src/heretic/p_inter.c:710` | same, `case SPR_FBMB` | `arti_firebomb` | `special` | **Time Bomb of the Ancients** (`TXT_ARTIFIREBOMB`, dstrings.h:41) | Same as #1. |
| 10 | `src/heretic/p_inter.c:717` | same, `case SPR_ATLP` | `arti_teleport` | `special` | **Chaos Device** (`TXT_ARTITELEPORT`, dstrings.h:42) | Same as #1. |
| 11 | `src/heretic/sb_bar.c:1200` | `CheatArtifact3Func` (sb_bar.c:1178), all-artifacts branch (`type == 26 && count == 0`, line 1189) | loop `i` = 1…10 (skipping `arti_superhealth`/`arti_teleport` in shareware, 1193–1197), 16 calls each (1198) | `NULL` | Keyboard cheat only. | Ignored. Message `TXT_CHEATARTIFACTS3` (dstrings.h:99) afterwards. |
| 12 | `src/heretic/sb_bar.c:1216` | `CheatArtifact3Func`, single-type branch (1205–1206) | `type` (1–10) × `count` (1–9) | `NULL` | Keyboard cheat only. | Ignored. |

The prototype at `src/heretic/p_local.h:273` is a declaration, not a call.

For pickups, `special`'s `MF_COUNTITEM` decides whether `itemcount` goes up.
For cheats, `mo` is `NULL`, so `itemcount` never changes.

### Demo reachability

**Not confirmed for any demo.** This can't be settled from the source alone.
It depends on the demo lump contents in `blasphem.wad`, and no instrumented
run has been done.

| Demo | Started at | Reaches `P_GiveArtifact`? | Gametics | In verification plan? |
|---|---|---|---|---|
| DEMO1 | `src/heretic/d_main.c:348` | **Not confirmed.** Only possible through call sites 1–10 (pickups). | 4227, **pinned** (`scripts/demo1-check.sh:15`) | Yes, pinned gate. |
| DEMO2 | `src/heretic/d_main.c:358` | **Not confirmed.** Same reason. | No recorded count in the repo. | No. |
| DEMO3 | `src/heretic/d_main.c:375` | **Not confirmed.** Same reason. | 2582 in the feasibility run (`-timedemo demo3`), **not yet pinned** | Yes, not yet pinned (see Verification plan). |

The gametic counts show the demos run to the end. They don't show whether
`P_GiveArtifact` is called.

Call sites 11–12 are **not reachable from demo playback**. Cheats come from
live key events: `G_Responder` → `SB_Responder` (`g_game.c:1021`,
`sb_bar.c:995–999`, `ev_keydown` only) → `HandleCheats` (`sb_bar.c:1015`).
Demo playback supplies ticcmds through `G_ReadDemoTiccmd`
(`g_game.c:1176–1177`), not key events, and the headless timedemo gets no
keyboard input.

---

## Verification plan

The plan covers two demos: DEMO1 (pinned) and DEMO3 (not yet pinned).

1. **DEMO1 (pinned).** `scripts/demo1-check.sh` must pass on **4227 gametics**
   (`EXPECTED_TICS` default, `scripts/demo1-check.sh:15`).
   - Exit code `255` from the engine is normal after a timedemo
     (`scripts/demo1-check.sh:48–51`).
   - The result comes from the `timed N gametics` line
     (`scripts/demo1-check.sh:57–62`), not from the exit code.
   - The wad sha256 is pinned
     (`e9ed3f53cb011f1ae897b66fcfe46692c8c2d73e147bbe1e36a9bf1f79a4cc63`,
     `scripts/demo1-check.sh:16`, checked at 35–38), and the wad is never
     modified.
   - Caveat: DEMO1 reachability is **not confirmed**, so a pass shows the port
     didn't break demo sync. It does not show the ported code ran.
2. **DEMO3 (not yet pinned).** Run the same headless timedemo with
   `demo3` in place of `demo1`, using the same binary, the same wad and the
   same sha256 check. The command is the `scripts/demo1-check.sh:49` form with
   `-timedemo demo3`.
   - Reference value: **2582 gametics**, from the feasibility run
     (`-timedemo demo3`). This number comes from the operator. The only places
     it appears in the repo are planning notes
     (`docs/context/2.2-pre-session-plan.md:40`,
     `docs/context/2.2-technique-plan.md:21`). There is no run log for it.
   - Status: **not yet pinned** until the per-tic demo test suite (Feature 1)
     exists. A mismatch should be reported and investigated, but it isn't a
     pinned gate the way DEMO1's 4227 is.
   - No script runs DEMO3 today. `scripts/demo1-check.sh` hard-codes `demo1`
     (`:49`), and only its tic count can be overridden (`EXPECTED_TICS`,
     `:15`). Running DEMO3 means the operator runs the command by hand, or a
     later script does. Writing that script is outside this agent's scope
     (`scripts/**` is read-only).
   - Same rules as DEMO1: exit code `255` is normal, the result comes from the
     `timed N gametics` line, and the wad sha256 is pinned and the wad is never
     modified.
   - Caveat: DEMO3 reachability is also **not confirmed**, so the same caveat
     applies.
3. **Coverage confirmation (operator action, not done).** To show whether
   DEMO1 or DEMO3 executes `P_GiveArtifact`, someone needs a temporary counter
   or a debugger breakpoint on `p_inter.c:425` during each timedemo. This needs
   either a `src/` change (outside this agent's write scope) or a gdb run by
   the operator. Until that's done, the reachability table above stays
   "Not confirmed" for both.
4. **Unit checks for the port** (run against the C original and the Rust
   port with the same `player_t` input):

- [ ] Empty inventory (`inventorySlotNum = 0`, `artifactCount = 0`):
      `P_GiveArtifact(p, arti_torch, NULL)` returns `true`, sets
      `inventory[0] = {arti_torch, 1}`, `inventorySlotNum = 1`,
      `artifactCount = 1`, `readyArtifact = arti_torch`, `itemcount`
      unchanged.
- [ ] Existing slot with count 15: returns `true`, count 16,
      `artifactCount` +1, `readyArtifact` unchanged (it was nonzero).
- [ ] Existing slot with count 16: returns `false`, and **no field changes**
      (including `itemcount`, even if `mo` has `MF_COUNTITEM`).
- [ ] New slot when `artifactCount > 0`: `readyArtifact` is not changed.
- [ ] `mo` non-NULL with `MF_COUNTITEM` set: `itemcount` +1. Without the flag:
      unchanged. `mo == NULL`: unchanged, with no dereference.
- [ ] Stale entry: after `P_PlayerRemoveArtifact` compacts the list, a stale
      `inventory[inventorySlotNum]` with the same `type` is overwritten to
      `{arti, 1}`, and `inventorySlotNum` +1 (same result as the C code).
- [ ] The all-artifacts cheat sequence (16 × each of 10 types from empty,
      non-shareware `gamemode`; shareware skips 2 types, sb_bar.c:1193–1197)
      ends with 10 slots of count 16, `artifactCount = 160`, and
      `readyArtifact` = the first type given (`arti_invulnerability`).
