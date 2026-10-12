# Port spec: `P_GiveBody` and `P_GiveArmor` (Heretic)

Source: `src/heretic/p_inter.c`

- `P_GiveBody`: lines 259–287 (header comment at 259–265, body at 267–287)
- `P_GiveArmor`: lines 289–309 (header comment at 289–295, body at 297–309)

Both functions are short and have no side effects beyond the fields listed
below. They make no calls, use no randomness, play no sounds and print no
messages. The callers handle all of that.

---

## Shared types

| Type | Definition | Notes |
|---|---|---|
| `boolean` | `src/doomtype.h:110` (`typedef int boolean;` when C++ or `<stdbool.h>`'s `__bool_true_false_are_defined` is set, which it is because `doomtype.h` includes `<stdbool.h>`). The fallback at `src/doomtype.h:114-118` is `enum { false, true }`. | Return values are always exactly `false` (0) or `true` (1). |
| `player_t` | `src/heretic/doomdef.h:422-473` (`struct player_s`) | |
| `mobj_t` | `src/heretic/doomdef.h` (ends at line 193; `int health;` at line 179) | Only reached through `player->mo`. |

Relevant `player_t` fields (`src/heretic/doomdef.h`):

| Field | Line | Type | Comment in source |
|---|---|---|---|
| `mo` | 424 | `mobj_t *` | |
| `health` | 436 | `int` | "only used between levels, mo->health" |
| `armorpoints`, `armortype` | 438 | `int`, `int` | "armor type is 0-2" |
| `chickenTics` | 469 | `int` | "player is a chicken if > 0" |

---

## 1. `P_GiveBody`

### Signature

```c
boolean P_GiveBody(player_t * player, int num);
```

- Defined at `src/heretic/p_inter.c:267`.
- Prototype at `src/heretic/p_local.h:274`, so it is visible to other modules.
- Header comment: "Returns false if the body isn't needed at all."

### Reference implementation (verbatim, p_inter.c:267-287)

```c
boolean P_GiveBody(player_t * player, int num)
{
    int max;

    max = MAXHEALTH;
    if (player->chickenTics)
    {
        max = MAXCHICKENHEALTH;
    }
    if (player->health >= max)
    {
        return (false);
    }
    player->health += num;
    if (player->health > max)
    {
        player->health = max;
    }
    player->mo->health = player->health;
    return (true);
}
```

### Algorithm / return-value rules

1. `max = MAXHEALTH` (100). If `player->chickenTics != 0` (any nonzero value,
   not just `> 0`), use `max = MAXCHICKENHEALTH` (30) instead.
2. **If `player->health >= max`, return `false`.** Nothing is written in
   this case. In particular `player->mo->health` is *not* synced.
3. Otherwise `player->health += num` with plain `int` addition. There is no
   overflow guard and no check on `num`, so a negative or zero `num` is
   accepted.
4. If the result is `> max`, clamp it to `max`. There is no lower clamp.
   A negative `num` can lower health, and the function still returns `true`.
5. Copy `player->health` into `player->mo->health`.
6. **Return `true`.** This happens whenever health was below `max` at entry,
   whatever `num` is.

Porting notes:

- The "full health" test uses `player->health` only, never `player->mo->health`.
  If the two differ at entry, the decision follows `player->health`. On the
  `true` path, `mo->health` is then overwritten with the new value.
- `player->mo` is dereferenced with no NULL check (only on the `true` path).
  A port should keep the precondition that `mo` is non-NULL.
- `max` is a local variable. It is not stored anywhere.

### Fields and globals read / written

| Item | Kind | Read | Written | Where (p_inter.c line) |
|---|---|---|---|---|
| `player->chickenTics` | `player_t` field | ✔ | | 272 |
| `player->health` | `player_t` field | ✔ | ✔ (only on the `true` path) | read 276, 280 (`+=`), 281, 285; written 280, 283 |
| `player->mo` | `player_t` field (pointer) | ✔ (only on the `true` path) | | 285 |
| `player->mo->health` | `mobj_t` field reached through player | | ✔ (only on the `true` path) | 285 |
| `num` | parameter | ✔ | | 280 |
| Globals | none | – | – | It touches no global variables. |

### Constants

| Name | Value | Defined at |
|---|---|---|
| `MAXHEALTH` | `100` | `src/heretic/p_local.h:36` |
| `MAXCHICKENHEALTH` | `30` | `src/heretic/p_local.h:37` |
| `false` / `true` | `0` / `1` | `<stdbool.h>` via `src/doomtype.h:102`; enum fallback `src/doomtype.h:114-118` |

### Call sites under `src/heretic`

| # | File:line | Enclosing function | `num` | Trigger | Use of return value |
|---|---|---|---|---|---|
| 1 | `src/heretic/p_inter.c:570` | `P_TouchSpecialThing` (p_inter.c:546) | `10` | Walking over a `SPR_PTN1` item: **Crystal Vial** (`Item_HealingPotion`; message `TXT_ITEMHEALTH` = "CRYSTAL VIAL", `src/heretic/dstrings.h:46`). Reached from `src/heretic/p_map.c:434` (`PIT_CheckThing`). | On `false`, `return`. The item stays, with no message or sound. On `true`, message and normal pickup. |
| 2 | `src/heretic/p_user.c:933` | `P_UseArtifact` (p_user.c:913), `case arti_health` | `25` | Using a **Quartz Flask** artifact (`arti_health`; `TXT_ARTIHEALTH` = "QUARTZ FLASK", dstrings.h:33). Reached from `P_PlayerUseArtifact` (p_user.c:887). | On `false`, `return (false)`. The artifact is not consumed. |
| 3 | `src/heretic/p_user.c:939` | `P_UseArtifact` (p_user.c:913), `case arti_superhealth` | `100` | Using a **Mystic Urn** artifact (`arti_superhealth`; `TXT_ARTISUPERHEALTH` = "MYSTIC URN", dstrings.h:39). | On `false`, `return (false)`. The artifact is not consumed. |
| 4 | `src/heretic/p_pspr.c:1812` | `A_GauntletAttack` (p_pspr.c:1761) | `damage >> 1` | Not a pickup. This is **Gauntlets of the Necromancer life-steal**, used only when `player->powers[pw_weaponlevel2]` is set (Tome of Power active) and the attack hit something (`linetarget` non-NULL). `damage = HITDICE(2)` = `(1+(P_Random()&7))*2` (`src/heretic/m_random.h:21`), giving 2–16, so `num` is 1–8. | Ignored. |
| – | `src/heretic/p_inter.c:404` | `P_GivePower` (p_inter.c:342) | `100` | **Dead code.** It sits inside a `/* ... */` block (p_inter.c:396-407) for a Doom-style `pw_strength` (berserk) branch. It is never compiled. List it for completeness only. | n/a |

The prototype at `src/heretic/p_local.h:274` is a declaration, not a call.

---

## 2. `P_GiveArmor`

### Signature

```c
boolean P_GiveArmor(player_t * player, int armortype);
```

- Defined at `src/heretic/p_inter.c:297`.
- **No header prototype.** `grep` finds no declaration in any `src/heretic/*.h`.
  It has external linkage because it is not `static`, but every use is in
  `p_inter.c` after the definition. A port can keep it file-local or expose it.
  Either works.
- Header comment: "Returns false if the armor is worse than the current armor."
  The real test is `>=`, so *equal* armor also returns `false`.

### Reference implementation (verbatim, p_inter.c:297-309)

```c
boolean P_GiveArmor(player_t * player, int armortype)
{
    int hits;

    hits = armortype * 100;
    if (player->armorpoints >= hits)
    {
        return (false);
    }
    player->armortype = armortype;
    player->armorpoints = hits;
    return (true);
}
```

### Algorithm / return-value rules

1. `hits = armortype * 100`. The factor `100` is a literal in the code, not
   a named constant. So armortype 1 gives 100 points and armortype 2 gives 200.
2. **If `player->armorpoints >= hits`, return `false`.** Nothing is written.
   The comparison is on points only. `player->armortype` is never read, so a
   worn-down type-2 armor with fewer than 100 points *is* replaced by a
   type-1 Silver Shield. The type then drops from 2 to 1 and the points reset to 100.
3. Otherwise set `player->armortype = armortype` and
   `player->armorpoints = hits`. Both are plain assignments, not additions.
4. **Return `true`.**

Porting notes:

- `armortype` is not validated. In-tree callers only pass `1` or `2`.
  With `0` or a negative value, `hits <= 0`, so the function returns `false`
  for any `armorpoints >= hits`, and that holds for every non-negative armor value.
- It does not touch `player->mo`, health, or any global.

### Fields and globals read / written

| Item | Kind | Read | Written | Where (p_inter.c line) |
|---|---|---|---|---|
| `player->armorpoints` | `player_t` field | ✔ | ✔ (only on the `true` path) | read 302; written 307 |
| `player->armortype` | `player_t` field | | ✔ (only on the `true` path) | 306 |
| `armortype` | parameter | ✔ | | 301, 306 |
| Globals | none | – | – | It touches no global variables. |

### Constants

| Name | Value | Defined at |
|---|---|---|
| (literal) points per armor class | `100` | Inline literal at `src/heretic/p_inter.c:301` (no `#define`) |
| `false` / `true` | `0` / `1` | `<stdbool.h>` via `src/doomtype.h:102`; enum fallback `src/doomtype.h:114-118` |
| Caller-supplied `armortype` values | `1`, `2` | Literals at the call sites below (no enum or `#define`) |

### Call sites under `src/heretic`

| # | File:line | Enclosing function | `armortype` | Trigger | Use of return value |
|---|---|---|---|---|---|
| 1 | `src/heretic/p_inter.c:577` | `P_TouchSpecialThing` (p_inter.c:546), `case SPR_SHLD` | `1` → 100 pts | Walking over a **Silver Shield** (`Item_Shield1`, mobj type `MT_ITEMSHIELD1` at `src/heretic/info.h:1390`; message `TXT_ITEMSHIELD1` = "SILVER SHIELD", `src/heretic/dstrings.h:48`) | On `false`, `return`. The item stays. On `true`, message and pickup. |
| 2 | `src/heretic/p_inter.c:584` | `P_TouchSpecialThing` (p_inter.c:546), `case SPR_SHD2` | `2` → 200 pts | Walking over an **Enchanted Shield** (`Item_Shield2`, `MT_ITEMSHIELD2` at `src/heretic/info.h:1391`; message `TXT_ITEMSHIELD2` = "ENCHANTED SHIELD", `src/heretic/dstrings.h:49`) | On `false`, `return`. The item stays. On `true`, message and pickup. |

No other file under `src/heretic` references `P_GiveArmor`. In particular, the
weapons/armor cheat (`CheatWeaponsFunc`, `src/heretic/sb_bar.c:1073`) does not call it. It writes
`player->armorpoints = 200` and `player->armortype = 2` directly (sb_bar.c:1077-1078).

---

## Verification checklist for the port

- [ ] `P_GiveBody` at full health (100, or 30 while `chickenTics != 0`) returns
      `false` and changes neither `player->health` nor `player->mo->health`.
- [ ] `P_GiveBody(p, 10)` at health 95 gives 100 and returns `true`, and
      `mo->health` is 100.
- [ ] A chicken at 25 health with `P_GiveBody(p, 25)` gives 30.
- [ ] `P_GiveBody` with negative `num` below max lowers health and returns `true`.
- [ ] `P_GiveArmor(p, 1)` with `armorpoints == 100` returns `false`. With
      `armorpoints == 99`, it returns `true` and sets type=1, points=100.
- [ ] `P_GiveArmor(p, 1)` with type=2, points=50 replaces it with type=1,
      points=100 and returns `true`.
- [ ] `P_GiveArmor(p, 2)` with points=150 sets type=2, points=200 and returns `true`.
